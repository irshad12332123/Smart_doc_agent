import json
import logging
import os
import shutil
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import bm25s
import Stemmer

from config.settings import BM25_INDEX_DIR
from lib.supabase import get_supabase_admin_client
from services.ingestion.base import BaseIngestion

logger = logging.getLogger(__name__)


def _data(response: Any) -> list[dict[str, Any]]:
    result = getattr(response, "data", response)
    return result if isinstance(result, list) else ([] if result is None else [result])


class SparseIngestion(BaseIngestion):
    """
    Sparse document indexing and synchronization service using BM25S.

    Workflow:
    1. Fetch all chunks and parent document titles from Supabase.
    2. Build an explicit mapping from BM25 integer positional index (0..N-1) to Supabase chunk IDs & metadata.
    3. Tokenize corpus text using BM25S tokenizer and PyStemmer (English).
    4. Index tokenized corpus with bm25s.BM25().
    5. Save BM25 index and chunk mapping locally to disk.
    6. Expose index regeneration to sync local sparse index whenever documents are uploaded or deleted.
    """

    _sync_lock = threading.Lock()

    def __init__(
        self,
        index_dir: str | Path | None = None,
        client: Optional[Any] = None,
    ):
        super().__init__(client=client)
        self.index_dir = Path(index_dir or BM25_INDEX_DIR)
        self.stemmer = Stemmer.Stemmer("english")

    def fetch_all_chunks(
        self,
        client: Optional[Any] = None,
        batch_size: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        Fetch all document chunks and their associated document titles from Supabase
        using pagination to handle large datasets seamlessly.
        """
        supabase_client = client or self.client
        all_chunks: list[dict[str, Any]] = []
        start = 0

        while True:
            end = start + batch_size - 1
            response = (
                supabase_client.table("document_chunks")
                .select("id, document_id, content, page_number, chunk_index, documents(title)")
                .order("id")
                .range(start, end)
                .execute()
            )
            rows = _data(response)
            if not rows:
                break
            all_chunks.extend(rows)
            if len(rows) < batch_size:
                break
            start += batch_size

        return all_chunks

    def build_and_save_index(
        self,
        chunks: list[dict[str, Any]],
        save_dir: str | Path | None = None
    ) -> dict[str, Any]:
        """
        Build BM25 index from a list of Supabase chunks, generate the index-to-chunk mapping,
        and persist both locally.
        """
        target_dir = Path(save_dir or self.index_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        mapping_file = target_dir / "chunk_mapping.json"
        metadata_file = target_dir / "metadata.json"

        # Edge case: No chunks in database
        if not chunks:
            logger.warning("No chunks found in Supabase to index for BM25.")
            with open(mapping_file, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2)

            metadata = {
                "total_chunks": 0,
                "status": "empty",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)

            return metadata

        # Step 1: Extract corpus and generate mapping of BM25 index -> Supabase chunk ID & metadata
        corpus: list[str] = []
        mapping: dict[int, dict[str, Any]] = {}

        for i, chunk in enumerate(chunks):
            content = (chunk.get("content") or "").strip()
            corpus.append(content)

            doc_info = chunk.get("documents") or {}
            title = doc_info.get("title") if isinstance(doc_info, dict) else ""

            mapping[i] = {
                "id": str(chunk["id"]),
                "chunk_id": str(chunk["id"]),
                "document_id": str(chunk["document_id"]),
                "doc_id": str(chunk["document_id"]),
                "content": chunk.get("content") or "",
                "text": chunk.get("content") or "",
                "page_number": chunk.get("page_number", 1),
                "chunk_index": chunk.get("chunk_index", 0),
                "title": title or "Untitled document",
            }

        # Step 2: Tokenize using bm25s and english stemmer
        corpus_tokens = bm25s.tokenize(
            corpus,
            stopwords="en",
            stemmer=self.stemmer,
            show_progress=False
        )

        # Step 3: Create and index with BM25
        retriever = bm25s.BM25()
        retriever.index(corpus_tokens, show_progress=False)

        # Step 4: Atomically save BM25 index artifacts and mapping to disk
        # We use a temporary directory first to prevent corrupted reads during re-indexing
        with tempfile.TemporaryDirectory(dir=target_dir.parent) as temp_dir:
            temp_path = Path(temp_dir) / "staging"
            temp_path.mkdir(parents=True, exist_ok=True)

            # Save BM25 index files (csc matrix, vocab, params)
            retriever.save(str(temp_path))

            # Save mapping file
            with open(temp_path / "chunk_mapping.json", "w", encoding="utf-8") as f:
                json.dump(mapping, f, indent=2)

            # Save metadata file
            metadata = {
                "total_chunks": len(chunks),
                "status": "ready",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "index_dir": str(target_dir.resolve()),
            }
            with open(temp_path / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)

            # Copy staged files to target directory
            for item in temp_path.iterdir():
                dest = target_dir / item.name
                if dest.is_dir():
                    shutil.rmtree(dest, ignore_errors=True)
                elif dest.exists():
                    dest.unlink()
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

        logger.info(f"BM25 index successfully built and saved with {len(chunks)} chunks at {target_dir}")
        return metadata

    def regenerate_index(
        self,
        client: Optional[Any] = None,
        save_dir: str | Path | None = None,
    ) -> dict[str, Any]:
        """
        Regenerate the BM25 index from scratch by fetching current chunks from Supabase.
        Thread-safe to prevent race conditions during concurrent uploads.
        """
        with self._sync_lock:
            logger.info("Starting BM25 sparse index regeneration from Supabase...")
            chunks = self.fetch_all_chunks(client=client or self.client)
            metadata = self.build_and_save_index(chunks, save_dir=save_dir)
            return metadata

    def ingest(self, *args, **kwargs) -> dict[str, Any]:
        """
        Ingest interface implementation. Synchronizes the sparse index with Supabase.
        """
        return self.regenerate_index()
