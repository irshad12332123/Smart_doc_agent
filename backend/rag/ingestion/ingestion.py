import hashlib
import json
import logging
from collections import Counter
from collections.abc import Iterator
import mimetypes
from pathlib import Path
from typing import Any
import uuid
from flask import Blueprint, Response, g, jsonify, request, stream_with_context
from groq import Groq
from werkzeug.utils import secure_filename

from modules.auth.middleware import require_auth
from language_models.services import CallLLM
from language_models.sml import load_slm
from config.settings import (
    S3_BUCKET_NAME,
    GROQ_MODEL,
    S3_SIGNED_URL_TTL_SECONDS,
    MAX_UPLOAD_BYTES,
)

from utils.get_file_type import get_file_type
from lib.aws_s3 import aws_s3_client
from lib.supabase import get_supabase_client
from query_engine.rewrite_query import rewrite_query
from query_engine.router import DocumentRouter
from s3.service import S3Service
from services.ingestion.dense import DenseIngestion
from services.ingestion.sparse import SparseIngestion
from services.retriever.sparse import SparseRetriever
from services.retriever.hybrid import HybridRetriever
from ingestion.ingest_repository import (
    create_job,
    get_job,
    update_job,
    find_document_by_hash,
)
from async_engine.tasks import process_ingestion_job, sync_sparse_index_task

logger = logging.getLogger(__name__)

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
    files = request.files.getlist("files")
    batch_ids = request.form.getlist("batch_ids")
    subject_id = request.form.get("subject_id") or None

    if not files:
        return jsonify({"detail": "Attach at least one file in the 'files' field."}), 400

    if not batch_ids:
        return jsonify({"detail": "At least one batch is required."}), 400

    bucket = _required_s3_bucket()
    uploaded_by = getattr(g.current_user, "id", None) if hasattr(g, "current_user") and g.current_user else None

    queued_jobs: list[dict[str, Any]] = []
    skipped_files: list[dict[str, Any]] = []

    try:
        for uploaded_file in files:
            filename = secure_filename(uploaded_file.filename or "")
            if not filename:
                continue

            file_bytes: bytes = uploaded_file.read()
            if not file_bytes:
                raise ValueError(f"File '{filename}' is empty")

            if len(file_bytes) > MAX_UPLOAD_BYTES:
                raise ValueError(f"File '{filename}' exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit")

            # 1. Hash file bytes with sha256
            file_sha256 = hashlib.sha256(file_bytes).hexdigest()

            # 2. Check if hash already exists in documents table (hash_key column)
            existing_doc = find_document_by_hash(file_sha256)
            if existing_doc:
                logger.info(f"File '{filename}' with hash {file_sha256} already exists in documents table.")
                skipped_files.append({
                    "filename": filename,
                    "file_sha256": file_sha256,
                    "document_id": str(existing_doc.get("id")),
                    "reason": "already_exists",
                    "message": f"File '{filename}' has already been ingested.",
                })
                continue

            # 3. Upload object to S3 before starting async processing
            category = get_file_type(filename)
            s3_key = f"{category}/{uuid.uuid4().hex}_{filename}"
            content_type = uploaded_file.mimetype or mimetypes.guess_type(filename)[0] or "application/octet-stream"
            aws_s3_client.put_object(Bucket=bucket, Key=s3_key, Body=file_bytes, ContentType=content_type)

            # 4. Create record in ingestion_jobs table
            job_record = create_job(
                s3_key=s3_key,
                file_sha256=file_sha256,
                max_attempts=5,
            )
            job_id = job_record["id"]

            # 5. Enqueue Celery task
            try:
                task = process_ingestion_job.delay(
                    job_id=job_id,
                    subject_id=subject_id,
                    batch_ids=batch_ids,
                    filename=filename,
                    uploaded_by=uploaded_by,
                )
                update_job(job_id, celery_task_id=task.id)
                queued_jobs.append({
                    "job_id": job_id,
                    "task_id": task.id,
                    "filename": filename,
                    "status": "queued",
                    "s3_key": s3_key,
                    "file_sha256": file_sha256,
                    "doc_id": job_id,
                })
            except Exception as celery_err:
                logger.error(f"Failed to enqueue Celery task for job {job_id}: {celery_err}")
                update_job(job_id, status="enqueue_failed", error=str(celery_err), error_type=type(celery_err).__name__)
                queued_jobs.append({
                    "job_id": job_id,
                    "task_id": None,
                    "filename": filename,
                    "status": "enqueue_failed",
                    "error": str(celery_err),
                    "s3_key": s3_key,
                    "file_sha256": file_sha256,
                    "doc_id": job_id,
                })

    except (RuntimeError, ValueError) as error:
        return jsonify({"detail": str(error)}), 400
    except Exception as e:
        logger.exception("Unexpected error during file ingestion enqueue:")
        return jsonify({"detail": "Document ingestion failed. Check the server logs.", "error": str(e)}), 500

    if skipped_files and not queued_jobs:
        return jsonify({
            "message": "All uploaded files have already been ingested.",
            "skipped": skipped_files,
            "jobs": [],
            "documents": [],
        }), 200

    return jsonify({
        "status": "queued",
        "message": f"Accepted: {len(queued_jobs)} document(s) queued for background ingestion.",
        "jobs": queued_jobs,
        "documents": queued_jobs,
        "skipped": skipped_files,
        "total_queued": len(queued_jobs),
        "total_skipped": len(skipped_files),
    }), 202

@ingest.route("/jobs/<job_id>", methods=["GET"])
def get_job_status(job_id: str):
    """Retrieve status and metadata of an ingestion job."""
    try:
        job = get_job(job_id)
        if not job:
            return jsonify({"detail": f"Job {job_id} not found"}), 404
        return jsonify({"job": job}), 200
    except Exception as e:
        return jsonify({"detail": f"Failed to get job status: {e}"}), 500

@ingest.route("/index/sync", methods=["POST"])
def sync_index():
    """Trigger BM25 sparse index regeneration asynchronously via Celery task."""
    try:
        task = sync_sparse_index_task.delay()
        return jsonify({
            "status": "queued",
            "message": "Sparse index regeneration queued asynchronously",
            "task_id": task.id,
        }), 202
    except Exception as e:
        logger.warning(f"Could not enqueue async sync index ({e}). Running synchronous fallback.")
        try:
            metadata = SparseIngestion().regenerate_index()
            return jsonify({
                "status": "success",
                "message": "Sparse BM25 index regenerated synchronously",
                "metadata": metadata,
            }), 200
        except Exception as sync_err:
            return jsonify({"detail": f"Failed to sync sparse index: {sync_err}"}), 500

@ingest.route("/retrieve/sparse", methods=["POST"])
def retrieve_sparse():
    """Retrieve document chunks using BM25 sparse retriever."""
    payload = request.get_json(silent=True) or {}
    query = payload.get("query")
    match_count = payload.get("match_count")
    match_threshold = payload.get("match_threshold", 0.0)
    document_ids = payload.get("document_ids")

    if not query or not isinstance(query, str) or not query.strip():
        return jsonify({"detail": "Query string is required"}), 400

    try:
        retriever = SparseRetriever()
        results = retriever.retrieve(
            query=query,
            match_count=match_count,
            match_threshold=match_threshold,
            document_ids=document_ids,
        )
        return jsonify({"query": query, "results": results, "count": len(results)}), 200
    except Exception as e:
        return jsonify({"detail": f"Sparse retrieval failed: {e}"}), 500

@ingest.route("/retrieve/hybrid", methods=["POST"])
def retrieve_hybrid():
    """Retrieve document chunks using Hybrid retriever (Dense + BM25S + RRF + optional CrossEncoder)."""
    payload = request.get_json(silent=True) or {}
    query = payload.get("query")
    match_count = payload.get("match_count")
    rerank = payload.get("rerank", False)
    dense_weight = payload.get("dense_weight", 1.0)
    sparse_weight = payload.get("sparse_weight", 1.0)
    document_ids = payload.get("document_ids")

    if not query or not isinstance(query, str) or not query.strip():
        return jsonify({"detail": "Query string is required"}), 400

    try:
        retriever = HybridRetriever()
        results = retriever.retrieve(
            query=query,
            match_count=match_count,
            dense_weight=dense_weight,
            sparse_weight=sparse_weight,
            rerank=rerank,
            document_ids=document_ids,
        )
        return jsonify({
            "query": query,
            "reranked": rerank,
            "results": results,
            "count": len(results),
        }), 200
    except Exception as e:
        return jsonify({"detail": f"Hybrid retrieval failed: {e}"}), 500

@ingest.route("/evaluation/run", methods=["POST", "GET"])
def run_evaluation():
    """Run retrieval benchmark evaluation on the college dataset."""
    try:
        from evaluation.evaluator import RetrievalEvaluator
        evaluator = RetrievalEvaluator()
        results = evaluator.run_all_evaluations(top_k=5)
        # Format summary metrics for JSON output
        summary = {name: data["metrics"] for name, data in results.items()}
        return jsonify({
            "status": "success",
            "summary": summary,
            "total_queries_tested": len(evaluator.queries),
        }), 200
    except Exception as e:
        return jsonify({"detail": f"Evaluation benchmark failed: {e}"}), 500

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
        # Regenerate sparse index after deletion to keep sync
        try:
            SparseIngestion().regenerate_index()
        except Exception as sparse_err:
            print("Warning: Sparse index regeneration failed after delete:", sparse_err)
        return "", 204
    except Exception:
        return jsonify({"detail": "Could not delete document."}), 500

@ingest.route("/documents/<document_id>/file", methods=["GET"])
def get_document_file(document_id: str):
    """Generate a presigned download URL for a document's S3 object."""
    try:
        client = get_supabase_client()
        res = client.table("documents").select("id, title, s3_key").eq("id", document_id).execute()
        rows = _data(res)
        if not rows or not rows[0].get("s3_key"):
            return jsonify({"detail": "Document not found or has no file attached"}), 404

        doc = rows[0]
        s3_service = S3Service()
        presigned_url = s3_service.generate_presigned_url(doc["s3_key"])
        if not presigned_url:
            return jsonify({"detail": "Unable to generate file download URL"}), 500

        return jsonify({
            "url": presigned_url,
            "expires_in": S3_SIGNED_URL_TTL_SECONDS,
            "filename": doc.get("title") or "document",
        }), 200
    except Exception as e:
        return jsonify({"detail": f"Failed to retrieve file URL: {e}"}), 500

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

    raw_subject_list = payload.get("subject_list") or payload.get("subjects") or []

    # Optional retrieval configuration from request body (with defaults)
    match_count = payload.get("match_count")
    rerank = payload.get("rerank", False)
    dense_weight = payload.get("dense_weight", 1.5)
    sparse_weight = payload.get("sparse_weight", 0.5)
    document_ids = payload.get("document_ids")

    if isinstance(raw_subject_list, list):
        subject_list_names = [
            str(s).strip() if isinstance(s, (str, int)) else str(s.get("name", "")).strip()
            for s in raw_subject_list
            if s
        ]
        subject_list_names = [s for s in subject_list_names if s]
    else:
        subject_list_names = []

    # Route query through deterministic metadata / document lookup layer
    router = DocumentRouter()
    router_result = router.route(
        query=message,
        subject_list=raw_subject_list,
        history=history,
    )

    def generate() -> Iterator[str]:
        try:
            # Case 1: Handled deterministically by metadata/document lookup
            if not router_result.should_invoke_rag:
                print(f"Deterministic lookup returned {len(router_result.documents)} documents")
                if router_result.documents:
                    yield _sse({"type": "documents", "documents": router_result.documents})

                content = router_result.formatted_text or "No matching documents found."
                yield _sse({"type": "token", "content": content})
                yield _sse({"type": "done"})
                return

            # Case 2: Normal RAG or hybrid fallback
            print("Router dispatching to Hybrid Retrieval")

            # Rewriting user query only for knowledge/RAG queries to improve embedding/BM25 retrieval
            rewritten_query = rewrite_query(message, GROQ_MODEL, history=history)
            rag_query = rewritten_query if rewritten_query else message

            hybrid_retriever = HybridRetriever()
            retrieved_rows = hybrid_retriever.retrieve(
                query=rag_query,
                match_count=match_count,
                dense_weight=dense_weight,
                sparse_weight=sparse_weight,
                rerank=rerank,
                document_ids=document_ids,
            )

            print("Hybrid retrieved rows count:", len(retrieved_rows))
            print("Hybrid retrieved rows:", retrieved_rows)

            sources = [
                {
                    "chunk_id": str(row.get("id") or row.get("chunk_id") or index),
                    "doc_id": str(row.get("document_id") or row.get("doc_id") or ""),
                    "filename": row.get("title") or row.get("filename") or "Untitled document",
                    "text": row.get("content") or row.get("text") or "",
                    "score": float(
                        row.get("cross_encoder_score")
                        or row.get("rrf_score")
                        or row.get("score")
                        or row.get("similarity")
                        or 0
                    ),
                    "page_number": row.get("page_number", 1),
                }
                for index, row in enumerate(retrieved_rows)
            ]

            yield _sse({"type": "sources", "sources": sources})

            if not sources:
                yield _sse({"type": "token", "content": "I couldn't find relevant passages in the uploaded documents."})
            else:
                context = "\n\n".join(
                    f"[{index}] {source['text']}"
                    for index, source in enumerate(sources, start=1)
                )
                for token in CallLLM().stream_answer(message, context, history, subject_list=subject_list_names):
                    yield _sse({"type": "token", "content": token})

            yield _sse({"type": "done"})

        except Exception as e:
            yield _sse({"type": "error", "content": f"Unable to answer that question right now. {e}"})

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache"}
    )
