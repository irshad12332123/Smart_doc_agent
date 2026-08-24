from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter

class Chunker:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200,separators=["\n\n", "\n", " ", ""])

    def chunk_docs(self, docs, s3_key: str) -> List[dict]:

        chunks: List[dict] = []
        split_chunks = self.text_splitter.split_documents(docs)

        for index, chunk in enumerate(split_chunks):
            chunks.append({
                "text": chunk.page_content,
                "metadata": {
                    "s3_key": s3_key,
                    "page": chunk.metadata.get("page", 0) + 1,  # 1-indexed page
                    "chunk_index": index,
                    "type": "pdf",
                }
            })

        return chunks


    def chunk_texts(self,texts, s3_key:str, chunk_size: int = 800) -> List[dict]:
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=150,separators=["\n\n", "\n", " ", ""])
        chunks: List[dict] = []

        text_chunks = text_splitter.split_text(texts)

        for index, chunk in enumerate(text_chunks):
            chunks.append({
                "text": chunk,
                "metadata": {
                    "s3_key": s3_key,
                    "page": index + 1,
                    "chunk_index": index,
                    "type": "text",
                }
            })

        return chunks
