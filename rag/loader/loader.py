"""Load supported files into LangChain ``Document`` objects."""

import os
import tempfile
from pathlib import Path
from typing import Sequence

from langchain_core.documents import Document
from langchain_community.document_loaders import Docx2txtLoader, PyMuPDFLoader, TextLoader


class Loader:
    """File loader that safely cleans up its temporary files."""

    def load(self, file_bytes: bytes, filename: str) -> list[Document]:
        suffix = Path(filename).suffix.lower()
        if suffix not in {".pdf", ".docx", ".txt", ".md", ".markdown"}:
            raise ValueError(f"Unsupported file type: {suffix or 'none'}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
            temporary_file.write(file_bytes)
            temporary_path = temporary_file.name

        try:
            if suffix == ".pdf":
                documents = PyMuPDFLoader(temporary_path).load()
            elif suffix == ".docx":
                documents = Docx2txtLoader(temporary_path).load()
            else:
                documents = TextLoader(temporary_path, encoding="utf-8", autodetect_encoding=True).load()

            for document in documents:
                document.metadata["source"] = filename
            return documents
        finally:
            if os.path.exists(temporary_path):
                os.remove(temporary_path)

    # Compatibility with callers that used the original method name.
    def PDFloader(self, file_bytes: bytes) -> Sequence[Document]:
        return self.load(file_bytes, "document.pdf")
