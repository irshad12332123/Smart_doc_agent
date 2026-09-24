
import json
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import  Any
from flask import Blueprint, Response, jsonify, request, stream_with_context
from groq import Groq

from services.retriever.dense import DenseRetriever
from modules.auth.middleware import require_auth
from language_models.services import CallLLM
from language_models.sml import load_slm
from config.settings import (
    S3_BUCKET_NAME,
)

from lib.aws_s3 import aws_s3_client
from lib.supabase import get_supabase_client
from services.ingestion.dense import DenseIngestion

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

@ingest.route("/ingest", methods=["POST"])
@require_auth
def ingest_files():
    print("request rceived")
    files = request.files.getlist("files")
    batch_ids = request.form.getlist("batch_ids")
    subject_id = request.form.get("subject_id") or None


    if not files:
        return jsonify({"detail": "Attach at least one file in the 'files' field."}), 400

    if not batch_ids:
        return jsonify({"detail": "At least one batch is required."}), 400

    supabase = get_supabase_client()
    del supabase

    completed: list[dict[str, Any]] = []

    try:
        bucket = _required_s3_bucket()

        #initializing the generator--
        context_meta_data_generator: Groq = load_slm()

        dense_ingester = DenseIngestion()

        for uploaded_file in files:
            completed.append(dense_ingester.ingest(uploaded_file, context_meta_data_generator, subject_id, batch_ids, aws_s3_client, bucket))

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

def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"

@ingest.route("/chat", methods=["POST"])
def chat():

    payload = request.get_json(silent=True) or {}
    print("payload", payload)
    message = payload.get("message")
    print("message", message)

    history = payload.get("history", [])

    if not isinstance(message, str) or not message.strip():
        return jsonify({"detail": "A non-empty message is required."}), 400
    if not isinstance(history, list):
        return jsonify({"detail": "History must be a list."}), 400

    def generate() -> Iterator[str]:
        try:

            print("Genrator started")
            dense_retriever = DenseRetriever()

            dense_retreived_rows = dense_retriever.retrieve(message)

            print("rows: ", dense_retreived_rows)

            sources = [
                {
                    "chunk_id": str(row.get("id") or row.get("chunk_id") or index),
                    "doc_id": str(row.get("document_id") or row.get("doc_id") or ""),
                    "filename": row.get("title") or row.get("filename") or "Untitled document",
                    "text": row.get("content") or row.get("text") or "",
                    "score": float(row.get("similarity") or row.get("score") or 0),
                }
                for index, row in enumerate(dense_retreived_rows)
            ]
            yield _sse({"type": "sources", "sources": sources})
            if not sources:
                yield _sse({"type": "token", "content": "I couldn't find relevant passages in the uploaded documents."})
            else:
                context = "\n\n".join(f"[{index}] {source['text']}" for index, source in enumerate(sources, start=1))
                for token in CallLLM().stream_answer(message, context, history):
                    yield _sse({"type": "token", "content": token})
            yield _sse({"type": "done"})
        except Exception as e:
            yield _sse({"type": "error", "content": f"Unable to answer that question right now. {e}"})

    return Response(stream_with_context(generate()), mimetype="text/event-stream", headers={"Cache-Control": "no-cache"})
