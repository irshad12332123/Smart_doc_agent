import logging
from typing import Any, List, Optional
from langchain_core.documents import Document
from langchain_experimental.text_splitter import (
    SemanticChunker,
    calculate_cosine_distances,
    combine_sentences,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

try:
    from embedder.embedding import Embedder
except ImportError:
    from rag.embedder.embedding import Embedder

class Chunker:

    def __init__(
        self,
        embedder: Optional[Any] = None,
        max_chunk_size: int = 1000,
        chunk_overlap: int = 100,
        breakpoint_threshold_type: str = "percentile",
        breakpoint_threshold_amount: float = 90,
    ):
        self.embedder = embedder or Embedder()
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap

        self.semantic_splitter = SemanticChunker(
            self.embedder,
            breakpoint_threshold_type=breakpoint_threshold_type,
            breakpoint_threshold_amount=breakpoint_threshold_amount,
        )
        self.recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )

    def _split_oversized_doc(
        self, doc: Document, max_chunk_size: int, chunk_overlap: int
    ) -> List[Document]:
        """Sub-split a Document recursively if its content exceeds max_chunk_size."""
        content = (doc.page_content or "").strip()
        if len(content) <= max_chunk_size:
            return [doc] if content else []

        splitter = (
            self.recursive_splitter
            if max_chunk_size == self.max_chunk_size and chunk_overlap == self.chunk_overlap
            else RecursiveCharacterTextSplitter(
                chunk_size=max_chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", " ", ""],
            )
        )

        splits = splitter.split_documents([doc])
        return [s for s in splits if s.page_content and s.page_content.strip()]

    def _split_oversized_text(
        self, text: str, max_chunk_size: int, chunk_overlap: int
    ) -> List[str]:
        """Sub-split raw text recursively if its length exceeds max_chunk_size."""
        content = (text or "").strip()
        if len(content) <= max_chunk_size:
            return [content] if content else []

        splitter = (
            self.recursive_splitter
            if max_chunk_size == self.max_chunk_size and chunk_overlap == self.chunk_overlap
            else RecursiveCharacterTextSplitter(
                chunk_size=max_chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", " ", ""],
            )
        )
        
        splits = splitter.split_text(content)
        return [s.strip() for s in splits if s and s.strip()]

    def semantic_chunk_documents(
        self,
        docs: List[Document],
        max_chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> List[Document]:
        """
        Split documents using batched semantic chunking. If any generated chunk exceeds
        max_chunk_size, recursively split it into smaller chunks.
        """
        valid_docs = [doc for doc in docs if doc.page_content and doc.page_content.strip()]
        if not valid_docs:
            return []

        max_size = max_chunk_size or self.max_chunk_size
        overlap = chunk_overlap if chunk_overlap is not None else self.chunk_overlap

        # 1. Batched semantic splitting across all documents
        semantic_docs: List[Document] = []
        try:
            doc_sentence_info = []
            all_sentences_list: List[str] = []

            for doc in valid_docs:
                s_list = self.semantic_splitter._get_single_sentences_list(doc.page_content)
                if len(s_list) <= 1:
                    doc_sentence_info.append({"single": True, "s_list": s_list, "doc": doc})
                else:
                    combined = combine_sentences(
                        [{"sentence": s, "index": i} for i, s in enumerate(s_list)],
                        self.semantic_splitter.buffer_size,
                    )
                    start_idx = len(all_sentences_list)
                    all_sentences_list.extend([x["combined_sentence"] for x in combined])
                    end_idx = len(all_sentences_list)
                    doc_sentence_info.append({
                        "single": False,
                        "sentences": combined,
                        "range": (start_idx, end_idx),
                        "doc": doc,
                    })

            # Embed all sentence combinations in one batched call
            all_embeddings = (
                self.embedder.generate_embeddings(all_sentences_list)
                if all_sentences_list
                else []
            )

            # Reconstruct semantic chunks per document using pre-computed embeddings
            for info in doc_sentence_info:
                if info["single"]:
                    if info["s_list"]:
                        semantic_docs.append(
                            Document(page_content=info["s_list"][0], metadata=info["doc"].metadata)
                        )
                    continue

                start_idx, end_idx = info["range"]
                sub_embeddings = all_embeddings[start_idx:end_idx]
                sentences = info["sentences"]
                for i, s in enumerate(sentences):
                    s["combined_sentence_embedding"] = sub_embeddings[i]

                distances, sentences = calculate_cosine_distances(sentences)
                if self.semantic_splitter.number_of_chunks is not None:
                    threshold = self.semantic_splitter._threshold_from_clusters(distances)
                    breakpoint_array = distances
                else:
                    threshold, breakpoint_array = (
                        self.semantic_splitter._calculate_breakpoint_threshold(distances)
                    )

                indices_above_thresh = [
                    i for i, x in enumerate(breakpoint_array) if x > threshold
                ]

                start = 0
                for idx in indices_above_thresh:
                    group = sentences[start : idx + 1]
                    combined_text = " ".join([d["sentence"] for d in group])
                    if (
                        self.semantic_splitter.min_chunk_size is None
                        or len(combined_text) >= self.semantic_splitter.min_chunk_size
                    ):
                        semantic_docs.append(
                            Document(page_content=combined_text, metadata=info["doc"].metadata)
                        )
                    start = idx + 1

                if start < len(sentences):
                    combined_text = " ".join([d["sentence"] for d in sentences[start:]])
                    if (
                        self.semantic_splitter.min_chunk_size is None
                        or len(combined_text) >= self.semantic_splitter.min_chunk_size
                    ):
                        semantic_docs.append(
                            Document(page_content=combined_text, metadata=info["doc"].metadata)
                        )

        except Exception as e:
            logger.warning(
                f"Batched semantic splitting encountered an issue ({e}). "
                "Falling back to recursive character splitter."
            )
            semantic_docs = self.recursive_splitter.split_documents(valid_docs)

        # 2. Check chunk size and fall back to recursive splitter if too large
        final_docs: List[Document] = []
        for doc in semantic_docs:
            if len(doc.page_content.strip()) > max_size:
                sub_docs = self._split_oversized_doc(
                    doc, max_chunk_size=max_size, chunk_overlap=overlap
                )
                final_docs.extend(sub_docs)
            elif doc.page_content and doc.page_content.strip():
                final_docs.append(doc)

        return final_docs

    def semantic_chunk_texts(
        self,
        text: str,
        max_chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> List[str]:
        """
        Split raw text using semantic chunking. If any chunk exceeds max_chunk_size,
        recursively split it into smaller chunks.
        """
        if not text or not text.strip():
            return []

        doc = Document(page_content=text.strip(), metadata={})
        split_docs = self.semantic_chunk_documents(
            [doc], max_chunk_size=max_chunk_size, chunk_overlap=chunk_overlap
        )
        return [
            d.page_content.strip()
            for d in split_docs
            if d.page_content and d.page_content.strip()
        ]

    def semantic_chunk(
        self,
        docs: List[Document],
        s3_key: str,
        max_chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> List[dict]:
        """
        Perform semantic chunking on documents with recursive splitter fallback on oversized chunks.
        Returns a list of structured chunk dicts.
        """
        return self.chunk_docs(
            docs=docs,
            s3_key=s3_key,
            max_chunk_size=max_chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def chunk_docs(
        self,
        docs: List[Document],
        s3_key: str,
        max_chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> List[dict]:
        """
        Chunk documents using semantic chunking with recursive fallback for oversized chunks.
        Formats results into the standard chunk dictionary structure.
        """
        if not docs:
            return []

        final_split_docs = self.semantic_chunk_documents(
            docs,
            max_chunk_size=max_chunk_size,
            chunk_overlap=chunk_overlap,
        )

        chunks: List[dict] = []
        for index, chunk in enumerate(final_split_docs):
            raw_page = chunk.metadata.get("page", 0)
            page_number = (raw_page + 1) if isinstance(raw_page, int) else 1
            doc_type = "pdf" if s3_key.lower().endswith(".pdf") else chunk.metadata.get("type", "document")

            chunks.append({
                "text": chunk.page_content.strip(),
                "metadata": {
                    "s3_key": s3_key,
                    "page": page_number,
                    "chunk_index": index,
                    "type": doc_type,
                },
            })

        return chunks

    def chunk_texts(
        self,
        texts: str,
        s3_key: str,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
    ) -> List[dict]:
        """
        Chunk text using semantic chunking with recursive fallback for oversized chunks.
        Formats results into the standard chunk dictionary structure.
        """
        if not texts or not texts.strip():
            return []

        text_chunks = self.semantic_chunk_texts(
            texts,
            max_chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        chunks: List[dict] = []
        for index, chunk in enumerate(text_chunks):
            chunks.append({
                "text": chunk,
                "metadata": {
                    "s3_key": s3_key,
                    "page": index + 1,
                    "chunk_index": index,
                    "type": "text",
                },
            })

        return chunks


# Alias for backward compatibility
SemanticChunkerWrapper = Chunker
