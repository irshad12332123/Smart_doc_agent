import json
from werkzeug.utils import secure_filename
from pathlib import Path
from config.settings import MAX_UPLOAD_BYTES
from lib.supabase import get_supabase_client
from services.ingestion.base import BaseIngestion
from utils.get_file_type import get_file_type
import mimetypes
import uuid
from pypdf import PdfReader
from io import BytesIO
from services.ingestion.constants import DocumentMetaData
from embedder.embedding import Embedder
from typing import Optional
from loader.loader import Loader
from chunker.splitter import Chunker
from config.settings import GROQ_MODEL
from groq import Groq
from typing import Any


def _data(response: Any) -> list[dict[str, Any]]:
    result = getattr(response, "data", response)
    return result if isinstance(result, list) else ([] if result is None else [result])


class DenseIngestion(BaseIngestion):

    def _insert_document(self, document_data: dict) -> str:

            response = get_supabase_client().table("documents").insert(document_data).execute()
            rows = _data(response)

            if not rows or not rows[0].get("id"):
                raise RuntimeError("The documents insert did not return a document id")
            return str(rows[0]["id"])

    def _ingest_bytes(self,file_bytes: bytes, filename: str, s3_key: str, document_id: str) -> int:
        documents = Loader().load(file_bytes, filename)
        if not documents:
            raise ValueError("No readable text was found in this document")

        chunks = Chunker().chunk_docs(documents, s3_key=s3_key)
        chunks = [chunk for chunk in chunks if chunk["text"].strip()]
        if not chunks:
            raise ValueError("No readable text was found in this document")

        embeddings = Embedder().generate_embeddings([chunk["text"] for chunk in chunks])
        rows = [
            {
                "document_id": document_id,
                "content": chunk["text"],
                "page_number": chunk["metadata"]["page"],
                "chunk_index": chunk["metadata"]["chunk_index"],
                "embedding": embedding,
            }
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        get_supabase_client().table("document_chunks").insert(rows).execute()
        return len(rows)

    def _upload_doc_id_per_batches(self, client, document_id: str, batch_ids: list[str]):

        document_batch_rows = [
                {
                    "document_id": document_id,
                    "batch_id": batch_id,
                }
                for batch_id in batch_ids
            ]
        (
            client
            .table("document_batches")
            .insert(document_batch_rows)
            .execute()
        )

    def _get_file_context_meta_data_from_slm(
        self,
        data: str,
        client: Optional[Groq] = None,
        model: str = GROQ_MODEL
    ) -> DocumentMetaData:
        print("data reveived: ", data)
        print("Started metadata extraction via Groq")

        if client is None:
            raise ValueError("No client passed in the meta dta extractor")

        system_prompt = """You are an expert metadata extractor. Extract details from the provided text into a valid JSON object matching this schema:
    {
        "description": "string (50-100 words summary)",
        "document_type": "notice" | "assignment" | "syllabus" | "notes" | "time_table" | "others",
        "deadline": "YYYY-MM-DD (optional, null if not present)"
    }
    Return ONLY a valid JSON object with no markdown wrappers or additional text."""

        # Using Groq's JSON object mode guarantees valid JSON output
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context Data:\n{data}"}
            ],
            model=model,
            temperature=0.1,  # Low temperature for deterministic metadata
            response_format={"type": "json_object"}
        )

        raw_response = chat_completion.choices[0].message.content
        if raw_response == None:
            raise ValueError("raw_response was None")
        parsed_json = json.loads(raw_response)

        print("Extracted metadata:", parsed_json)
        return DocumentMetaData.model_validate(parsed_json)

    def ingest(self, uploaded_file,  context_meta_data_generator, subject_id: str | None, batch_ids: list[str],  aws_s3_client, bucket:str):

        filename = secure_filename(uploaded_file.filename or "")

        if not filename:
            raise ValueError("Every upload must have a filename")

        extension = Path(filename).suffix.lower().lstrip(".")
        category = get_file_type(filename)

        file_bytes: bytes = uploaded_file.read()

        if extension == "pdf":
            reader = PdfReader(BytesIO(file_bytes))
            extracted_text = "\n".join(
                page.extract_text() or ""
                for page in reader.pages
            )
        else:
            extracted_text = file_bytes.decode("utf-8")

        if not file_bytes:
                    raise ValueError(f"{filename} is empty")

        if len(file_bytes) > MAX_UPLOAD_BYTES:
            raise ValueError(f"{filename} exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit")

        file_context_meta_data: DocumentMetaData =self. _get_file_context_meta_data_from_slm(extracted_text, context_meta_data_generator)

        s3_key = f"{category}/{uuid.uuid4().hex}_{filename}"

        from flask import g

        document_data_to_insert: dict = {
            **file_context_meta_data.model_dump(),
            "title" : filename,
            "s3_key" : s3_key,
            "uploaded_by": g.current_user.id
            }

        if subject_id is not None:
            document_data_to_insert["subject_id"] = subject_id

        document_id = self._insert_document(document_data_to_insert)

        self._upload_doc_id_per_batches(get_supabase_client(), document_id, batch_ids)

        content_type = uploaded_file.mimetype or mimetypes.guess_type(filename)[0] or "application/octet-stream"

        chunk_count =self. _ingest_bytes(file_bytes, filename, s3_key, document_id)

        aws_s3_client.put_object(Bucket=bucket, Key=s3_key, Body=file_bytes, ContentType=content_type)

        return dict({
            "doc_id": document_id,
            "filename": filename,
            "filetype": Path(filename).suffix.lower().lstrip("."),
            "num_chunks": chunk_count,
        })
