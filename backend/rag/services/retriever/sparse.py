import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Optional

import bm25s
import Stemmer

from config.settings import BM25_DEFAULT_K, BM25_INDEX_DIR, RETRIEVAL_MATCH_COUNT
from services.retriever.base import BaseRetriever
from services.ingestion.sparse import SparseIngestion

logger = logging.getLogger(__name__)

class SparseRetriever(BaseRetriever):
    """
    Sparse Document Retriever using BM25S with English PyStemmer.

    Features:
    - Tokenizes queries with the same stemming/stopwords configuration as the indexer.
    - Loads local BM25 index artifacts and chunk_mapping.json.
    - Resolves BM25 integer positions back to Supabase chunk IDs and metadata.
    - Automatically builds the index on first run if not present locally.
    - Thread-safe reloading for instant synchronization after new document uploads.
    """

    def __init__(
        self,
        index_dir: str | Path | None = None,
        auto_load: bool = True,
        auto_build_if_missing: bool = True,
    ):
        self.index_dir = Path(index_dir or BM25_INDEX_DIR)
        self.stemmer = Stemmer.Stemmer("english")
        self.retriever: Optional[bm25s.BM25] = None
        self.chunk_mapping: dict[int, dict[str, Any]] = {}
        self.metadata: dict[str, Any] = {}
        self._lock = threading.Lock()
        self._last_loaded_mtime: float = 0.0

        if auto_load:
            self.load_index(auto_build_if_missing=auto_build_if_missing)

    def is_index_ready(self) -> bool:
        """Check if index files and mapping exist and are loaded."""
        mapping_file = self.index_dir / "chunk_mapping.json"
        params_file = self.index_dir / "params.index.json"
        return mapping_file.exists() and (params_file.exists() or len(self.chunk_mapping) == 0)

    def load_index(self, auto_build_if_missing: bool = True) -> bool:
        """
        Load BM25 index and chunk mapping from local storage.
        If missing and auto_build_if_missing is True, builds the index from Supabase.
        """
        with self._lock:
            mapping_file = self.index_dir / "chunk_mapping.json"
            params_file = self.index_dir / "params.index.json"
            metadata_file = self.index_dir / "metadata.json"

            # If index is missing or incomplete, build from Supabase
            if not mapping_file.exists() or (not params_file.exists() and auto_build_if_missing):
                if auto_build_if_missing:
                    logger.info("Local BM25 index not found. Building initial index from Supabase...")
                    SparseIngestion(self.index_dir).regenerate_index()
                else:
                    return False

            # Load chunk mapping
            if mapping_file.exists():
                with open(mapping_file, "r", encoding="utf-8") as f:
                    raw_mapping = json.load(f)
                    self.chunk_mapping = {int(k): v for k, v in raw_mapping.items()}
                self._last_loaded_mtime = os.path.getmtime(mapping_file)
            else:
                self.chunk_mapping = {}

            # Load metadata
            if metadata_file.exists():
                with open(metadata_file, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)

            # Load BM25 model if chunks exist
            if len(self.chunk_mapping) > 0 and params_file.exists():
                try:
                    self.retriever = bm25s.BM25.load(str(self.index_dir), load_corpus=False)
                    logger.info(f"Loaded BM25 index with {len(self.chunk_mapping)} chunks.")
                    return True
                except Exception as e:
                    logger.error(f"Failed to load BM25 index from {self.index_dir}: {e}")
                    self.retriever = None
                    return False
            else:
                self.retriever = None
                return True

    def reload_index(self) -> bool:
        """Explicitly reloads the index from disk (called after new upload / sync)."""
        return self.load_index(auto_build_if_missing=False)

    def _check_and_auto_reload(self):
        """Auto-reload if the index files on disk have been updated by another process or thread."""
        mapping_file = self.index_dir / "chunk_mapping.json"
        if mapping_file.exists():
            current_mtime = os.path.getmtime(mapping_file)
            if current_mtime > self._last_loaded_mtime:
                self.load_index(auto_build_if_missing=False)

    def retrieve(
        self,
        query: str,
        match_count: int | None = None,
        match_threshold: float = 0.0,
        document_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant document chunks for the given search query using BM25S.

        Steps:
        1. Validate query and ensure index is loaded.
        2. Tokenize search query with PyStemmer.
        3. Retrieve top-k scored document indices from BM25 index.
        4. Map integer indices back to Supabase chunk IDs, document metadata, and text.
        5. Filter results by threshold and optional document_id restrictions.
        6. Return list of chunk result dictionaries compatible with the RAG pipeline.
        """
        if not isinstance(query, str) or not query.strip():
            return []

        # Auto-reload if index was updated on disk
        self._check_and_auto_reload()

        if self.retriever is None or not self.chunk_mapping:
            # Attempt loading/building once
            if not self.load_index(auto_build_if_missing=True) or self.retriever is None or not self.chunk_mapping:
                return []

        # Step 1: Tokenize query
        query_tokens = bm25s.tokenize(
            [query.strip()],
            stemmer=self.stemmer,
            stopwords="en",
            show_progress=False,
        )

        # Step 2: Determine retrieval count k (bm25s requires k <= total indexed documents)
        total_chunks = len(self.chunk_mapping)
        requested_k = match_count or BM25_DEFAULT_K or RETRIEVAL_MATCH_COUNT
        k = min(requested_k, total_chunks)

        if k <= 0:
            return []

        # Step 3: Run BM25 retrieval
        try:
            doc_indices, scores = self.retriever.retrieve(
                query_tokens,
                k=k,
                show_progress=False,
            )
        except Exception as e:
            logger.error(f"Error during BM25 retrieval: {e}")
            return []

        if len(doc_indices) == 0 or len(doc_indices[0]) == 0:
            return []

        # Step 4: Map BM25 integer indices to Supabase chunk IDs and metadata
        doc_ids_filter_set = set(document_ids) if document_ids else None
        retrieved_results: list[dict[str, Any]] = []

        for idx, score_val in zip(doc_indices[0], scores[0]):
            bm25_idx = int(idx)
            score = float(score_val)

            # Filter non-matching / below-threshold scores if threshold is specified
            if score < match_threshold or score <= 0.0:
                continue

            chunk_meta = self.chunk_mapping.get(bm25_idx)
            if not chunk_meta:
                continue

            doc_id = str(chunk_meta.get("document_id") or chunk_meta.get("doc_id") or "")

            # Filter by document_id if scoped retrieval requested
            if doc_ids_filter_set is not None and doc_id not in doc_ids_filter_set:
                continue

            chunk_id = str(chunk_meta.get("id") or chunk_meta.get("chunk_id") or "")
            content = str(chunk_meta.get("content") or chunk_meta.get("text") or "")
            title = str(chunk_meta.get("title") or "Untitled document")
            page_number = int(chunk_meta.get("page_number") or 1)
            chunk_index = int(chunk_meta.get("chunk_index") or 0)

            retrieved_results.append({
                "id": chunk_id,
                "chunk_id": chunk_id,
                "document_id": doc_id,
                "doc_id": doc_id,
                "content": content,
                "text": content,
                "similarity": score,
                "score": score,
                "title": title,
                "page_number": page_number,
                "chunk_index": chunk_index,
            })

        return retrieved_results

# Backward compatibility alias
SparseDocumentSystem = SparseRetriever
