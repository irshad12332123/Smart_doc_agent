from typing import Any, List, Optional
from langchain_core.documents import Document
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import RecursiveCharacterTextSplitter

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
        Split documents using semantic chunking. If any generated chunk exceeds
        max_chunk_size, recursively split it into smaller chunks.
        """
        valid_docs = [doc for doc in docs if doc.page_content and doc.page_content.strip()]
        if not valid_docs:
            return []

        max_size = max_chunk_size or self.max_chunk_size
        overlap = chunk_overlap if chunk_overlap is not None else self.chunk_overlap

        # 1. Semantic splitting
        semantic_docs = self.semantic_splitter.split_documents(valid_docs)

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

        max_size = max_chunk_size or self.max_chunk_size
        overlap = chunk_overlap if chunk_overlap is not None else self.chunk_overlap

        # 1. Semantic splitting
        semantic_chunks = self.semantic_splitter.split_text(text)

        # 2. Fall back to recursive splitter for oversized chunks
        final_chunks: List[str] = []
        for chunk in semantic_chunks:
            chunk_stripped = chunk.strip()
            if not chunk_stripped:
                continue
            if len(chunk_stripped) > max_size:
                sub_chunks = self._split_oversized_text(
                    chunk_stripped, max_chunk_size=max_size, chunk_overlap=overlap
                )
                final_chunks.extend(sub_chunks)
            else:
                final_chunks.append(chunk_stripped)

        return final_chunks

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
