"""HTTP endpoints for document ingestion, retrieval, and chat."""

import json
import mimetypes
import uuid
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import  Any
from transformers.pipelines.text_generation  import TextGenerationPipeline

from flask import Blueprint, Response, jsonify, request, stream_with_context
from werkzeug.utils import secure_filename

from modules.auth.middleware import require_auth
from language_models.services import CallLLM
from chunker.splitter import Chunker
from config.settings import (
    MAX_UPLOAD_BYTES,
    RETRIEVAL_MATCH_COUNT,
    RETRIEVAL_MATCH_THRESHOLD,
    S3_BUCKET_NAME,
    SLM_MODEL_NAME
)

from embedder.embedding import Embedder
from lib.aws_s3 import aws_s3_client
from lib.supabase import get_supabase_client
from loader.loader import Loader
from utils.get_file_type import get_file_type
from ingestion.constants import DocumentMetaData, DocumentIdMetaData
from language_models.sml import load_slm

ingest = Blueprint("ingest", __name__, url_prefix="/api")

def _data(response: Any) -> list[dict[str, Any]]:
    result = getattr(response, "data", response)
    return result if isinstance(result, list) else ([] if result is None else [result])


def _required_s3_bucket() -> str:
    if not S3_BUCKET_NAME:
        raise RuntimeError("S3_BUCKET_NAME must be configured")
    return S3_BUCKET_NAME


def _document_info(document: dict[str, Any], chunk_counts: Counter[str]) -> dict[str, Any]:
    document_id = str(document.get("id") or document.get("document_id"))
    title = document.get("title") or document.get("filename") or "Untitled document"
    return {
        "doc_id": document_id,
        "filename": title,
        "filetype": Path(title).suffix.lower().lstrip("."),
        "num_chunks": chunk_counts[document_id],
        "uploaded_at": document.get("created_at") or "",
    }


def _insert_document(document_data: dict) -> str:

    response = get_supabase_client().table("documents").insert(document_data).execute()
    rows = _data(response)

    if not rows or not rows[0].get("id"):
        raise RuntimeError("The documents insert did not return a document id")
    return str(rows[0]["id"])

def _ingest_bytes(file_bytes: bytes, filename: str, s3_key: str, document_id: str) -> int:
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
            "s3_key": s3_key,
        }
        for chunk, embedding in zip(chunks, embeddings, strict=True)
    ]
    get_supabase_client().table("document_chunks").insert(rows).execute()
    return len(rows)

def _upload_doc_id_per_batches(client, document_id: str, batch_ids: list[str]):

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

def _get_file_context_meta_data_from_slm(data: str, generator: TextGenerationPipeline) -> DocumentMetaData:

    prompt: str = f"""
    You are an expert metadata extractor. Extract details from the text below into a valid JSON object.
    Do not output markdown, explanations, or extra text. ONLY valid JSON.

    JSON Schema:
    {{
        "description": "string (50-100 words summary)",
        "document_type": "notice" | "assignment" | "syllabus" | "notes" | "time_table" | "others",
        "deadline": "YYYY-MM-DD (optional, omit if not present)",
    }}

    Context Data:
    {data}

    Do not include markdown.
    Do not include explanations.
    """
    generator = load_slm()


    result = generator(
    prompt,
    max_new_tokens=300,
    return_full_text=False,
)

    generated_text = result[0]["generated_text"]

    data = json.loads(generated_text)


    return DocumentMetaData.model_validate(data)

# def _get_doc_required_meta_uuids(batch_id: list[str], user_id: str) -> DocumentIdMetaData:

    if len(batch_id) < 1:
        raise ValueError ("Batch details missing")

    client = get_supabase_client()

    subject = (
        client
        .table("batches")
        .select("current_semester_id", "course_id")
        .eq("id", batch_id)
        .single()
        .execute()
    )

    if subject is None:
        raise ValueError ("Subject not found")

    return DocumentIdMetaData(
        subject_id=subject_id,
    )

@ingest.route("/ingest", methods=["POST"])
@require_auth
def ingest_files():
    print("request rceived")
    files = request.files.getlist("files")
    print(files)
    batch_ids = request.form.getlist("batch_ids")
    subject_id = request.form.get("subject_id") or None

    if not files:
        return jsonify({"detail": "Attach at least one file in the 'files' field."}), 400

    if not batch_ids:
        return jsonify({"detail": "At least one batch is required."}), 400

    supabase = get_supabase_client()  # Fail before uploading a file if configuration is absent.
    del supabase

    completed: list[dict[str, Any]] = []

    try:
        bucket = _required_s3_bucket()

        #initializing the generator--
        context_meta_data_generator: TextGenerationPipeline = load_slm()

        for uploaded_file in files:
            filename = secure_filename(uploaded_file.filename or "")

            if not filename:
                raise ValueError("Every upload must have a filename")

            category = get_file_type(filename)

            file_bytes: bytes = uploaded_file.read()

            if not file_bytes:
                raise ValueError(f"{filename} is empty")

            if len(file_bytes) > MAX_UPLOAD_BYTES:
                raise ValueError(f"{filename} exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit")

            s3_key = f"{category}/{uuid.uuid4().hex}_{filename}"

            content_type = uploaded_file.mimetype or mimetypes.guess_type(filename)[0] or "application/octet-stream"
            aws_s3_client.put_object(Bucket=bucket, Key=s3_key, Body=file_bytes, ContentType=content_type)

            file_context_meta_data: DocumentMetaData = _get_file_context_meta_data_from_slm(file_bytes.decode("utf-8"), context_meta_data_generator)

            document_data_to_insert: dict = {
                **file_context_meta_data.model_dump(),
                "title" : filename,
                "s3_key" : s3_key
               }

            if subject_id is not None:
                document_data_to_insert["subject_id"] = subject_id

            document_id = _insert_document(document_data_to_insert)

            _upload_doc_id_per_batches(get_supabase_client(), document_id, batch_ids)

            chunk_count = _ingest_bytes(file_bytes, filename, s3_key, document_id)

            completed.append({
                "doc_id": document_id,
                "filename": filename,
                "filetype": Path(filename).suffix.lower().lstrip("."),
                "num_chunks": chunk_count,
            })

    except (RuntimeError, ValueError) as error:
        return jsonify({"detail": str(error)}), 400
    except Exception as e:
        return jsonify({"detail": "Document ingestion failed. Check the server logs.", "error": e}), 500

    return jsonify({"documents": completed, "total_chunks_added": sum(d["num_chunks"] for d in completed)}), 201

@ingest.route("/documents", methods=["GET"])
def list_documents():
    try:
        client = get_supabase_client()
        documents = _data(client.table("documents").select("id,title,s3_key,created_at").execute())
        chunks = _data(client.table("document_chunks").select("document_id").execute())
        counts = Counter(str(chunk["document_id"]) for chunk in chunks)
        return jsonify([_document_info(document, counts) for document in documents])
    except Exception:
        return jsonify({"detail": "Could not load documents."}), 500

@ingest.route("/documents/<document_id>", methods=["DELETE"])
def delete_document(document_id: str):
    try:
        client = get_supabase_client()
        document_rows = _data(client.table("documents").select("s3_key").eq("id", document_id).execute())
        client.table("document_chunks").delete().eq("document_id", document_id).execute()
        client.table("documents").delete().eq("id", document_id).execute()
        if document_rows and document_rows[0].get("s3_key") and S3_BUCKET_NAME:
            aws_s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=document_rows[0]["s3_key"])
        return "", 204
    except Exception:
        return jsonify({"detail": "Could not delete document."}), 500


def _retrieve(query: str) -> list[dict[str, Any]]:
    embedding = Embedder().generate_embeddings([query])[0]
    client = get_supabase_client()
    # ``match_document_chunks`` is the conventional Supabase pgvector RPC name.
    result = client.rpc(
        "match_document_chunks",
        {
            "query_embedding": embedding,
            "match_threshold": RETRIEVAL_MATCH_THRESHOLD,
            "match_count": RETRIEVAL_MATCH_COUNT,
        },
    ).execute()
    return _data(result)


def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"

@ingest.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    message = payload.get("message")
    history = payload.get("history", [])

    if not isinstance(message, str) or not message.strip():
        return jsonify({"detail": "A non-empty message is required."}), 400
    if not isinstance(history, list):
        return jsonify({"detail": "History must be a list."}), 400

    def generate() -> Iterator[str]:
        try:
            rows = _retrieve(message)
            sources = [
                {
                    "chunk_id": str(row.get("id") or row.get("chunk_id") or index),
                    "doc_id": str(row.get("document_id") or row.get("doc_id") or ""),
                    "filename": row.get("title") or row.get("filename") or "Untitled document",
                    "text": row.get("content") or row.get("text") or "",
                    "score": float(row.get("similarity") or row.get("score") or 0),
                }
                for index, row in enumerate(rows)
            ]
            yield _sse({"type": "sources", "sources": sources})
            if not sources:
                yield _sse({"type": "token", "content": "I couldn't find relevant passages in the uploaded documents."})
            else:
                context = "\n\n".join(f"[{index}] {source['text']}" for index, source in enumerate(sources, start=1))
                for token in CallLLM().stream_answer(message, context, history):
                    yield _sse({"type": "token", "content": token})
            yield _sse({"type": "done"})
        except Exception:
            yield _sse({"type": "error", "content": "Unable to answer that question right now."})

    return Response(stream_with_context(generate()), mimetype="text/event-stream", headers={"Cache-Control": "no-cache"})
