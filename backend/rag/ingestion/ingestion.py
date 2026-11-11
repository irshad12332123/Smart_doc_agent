
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
from werkzeug.utils import secure_filename

from modules.auth.middleware import require_auth
from modules.auth.middleware import require_role
from config.settings import (
    S3_BUCKET_NAME,
    S3_SIGNED_URL_TTL_SECONDS,
    MAX_UPLOAD_BYTES,
)

from utils.get_file_type import get_file_type
from lib.aws_s3 import aws_s3_client
from lib.supabase import get_supabase_client
from s3.service import S3Service
from services.ingestion.sparse import SparseIngestion
from services.retriever.sparse import SparseRetriever
from services.retriever.hybrid import HybridRetriever
try:
    from query_graph import query_graph, RAGState
except ImportError:
    try:
        from rag.query_graph import query_graph, RAGState
    except ImportError:
        from backend.rag.query_graph import query_graph, RAGState
from ingestion.ingest_repository import (
    create_job,
    get_job,
    update_job,
    find_document_by_hash,
)
from async_engine.tasks import process_ingestion_job, sync_sparse_index_task
from rag.modules.auth.constants import AuthorizedRolesToAcessUpload
from rag.modules.user.services import get_subjects

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
        "description": document.get("description") or "",
        "document_type": document.get("document_type") or "",
        "unit": document.get("unit"),
    }

@ingest.route("/ingest", methods=["POST"])
@require_role(*AuthorizedRolesToAcessUpload) # this internally handles the authorization
def ingest_files():
    files = request.files.getlist("files")
    batch_ids = request.form.getlist("batch_ids")
    batch_id = request.form.get("batch_id") or request.form.get("batchId")
    if not batch_ids and batch_id:
        batch_ids = [batch_id]
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
                    batch_id=batch_id or (batch_ids[0] if batch_ids else None),
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
@require_auth
def list_documents():
    try:
        client = get_supabase_client()
        # Accept batch_id from query parameters (or json body fallback if provided)
        user_batch_id = (
            request.args.get("batch_id")
            or request.args.get("batchId")
            or (request.get_json(silent=True) or {}).get("batch_id")
            or (request.get_json(silent=True) or {}).get("batchId")
        )

        # Fallback: Auto-resolve batch_id from student profile if caller didn't pass it
        if not user_batch_id and getattr(g, "current_profile", {}).get("role") == "student":
            try:
                from modules.user.services import _get_single_row_from_supabase_where
                student_record = _get_single_row_from_supabase_where(
                    ["id"], ["profile_id", str(g.current_user.id)], "students", client=client
                )
                if student_record and student_record.get("id"):
                    membership = _get_single_row_from_supabase_where(
                        ["batch_id"], ["student_id", student_record["id"]], "batch_memberships", client=client
                    )
                    if membership and membership.get("batch_id"):
                        user_batch_id = membership["batch_id"]
            except Exception as ex:
                logger.warning(f"Could not auto-resolve batch_id for student: {ex}")

        if user_batch_id:
            # Check document_batches junction table as documents may be mapped there or via documents.batch_id
            doc_batches = _data(
                client.table("document_batches").select("document_id").eq("batch_id", user_batch_id).execute()
            )
            batch_doc_ids = [str(r["document_id"]) for r in doc_batches if r.get("document_id")]

            if batch_doc_ids:
                documents = _data(
                    client.table("documents")
                    .select("id,title,s3_key,created_at,description,document_type,unit")
                    .or_(f"batch_id.eq.{user_batch_id},id.in.({','.join(batch_doc_ids)})")
                    .execute()
                )
            else:
                documents = _data(
                    client.table("documents")
                    .select("id,title,s3_key,created_at,description,document_type,unit")
                    .eq("batch_id", user_batch_id)
                    .execute()
                )
        else:
            documents = _data(
                client.table("documents")
                .select("id,title,s3_key,created_at,description,document_type,unit")
                .execute()
            )

        print(f"Documents Gathered: {len(documents)}")
        chunks = _data(client.table("document_chunks").select("document_id").execute())
        counts = Counter(str(chunk["document_id"]) for chunk in chunks)
        return jsonify([_document_info(document, counts) for document in documents])
    except Exception as e:
        logger.error(f"Error fetching documents: {e}")
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
@require_auth
def get_document_file(document_id: str):
    """Generate a presigned download/view URL for a document's S3 object."""
    try:
        client = get_supabase_client()
        res = client.table("documents").select("id, title, s3_key").eq("id", document_id).execute()
        rows = _data(res)
        if not rows or not rows[0].get("s3_key"):
            return jsonify({"detail": "Document not found or has no file attached"}), 404

        doc = rows[0]
        filename = doc.get("title") or "document"
        download_requested = request.args.get("download", "").lower() in ("true", "1", "yes")

        s3_service = S3Service()
        presigned_url = s3_service.generate_presigned_url(
            doc["s3_key"],
            filename=filename,
            download=download_requested,
        )
        if not presigned_url:
            return jsonify({"detail": "Unable to generate file download URL"}), 500

        return jsonify({
            "url": presigned_url,
            "expires_in": S3_SIGNED_URL_TTL_SECONDS,
            "filename": filename,
        }), 200
    except Exception as e:
        return jsonify({"detail": f"Failed to retrieve file URL: {e}"}), 500

def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"

@ingest.route("/query", methods=["POST"])
def query():
    """
    Orchestrated RAG query endpoint powered by LangGraph query_graph.invoke().
    Executes conditional agentic decision support, exact metadata search,
    hybrid retrieval, evidence evaluation, query rewriting loop, and answer generation.
    """
    payload = request.get_json(silent=True) or {}
    query_text = payload.get("query") or payload.get("message")
    history = payload.get("history", [])

    if not isinstance(query_text, str) or not query_text.strip():
        return jsonify({"detail": "A non-empty query string is required."}), 400
    if not isinstance(history, list):
        return jsonify({"detail": "History must be a list."}), 400

    raw_subject_list = payload.get("subject_list") or payload.get("subjects") or []
    match_count = payload.get("match_count")
    rerank = payload.get("rerank", False)
    dense_weight = payload.get("dense_weight", 1.5)
    sparse_weight = payload.get("sparse_weight", 0.5)
    document_ids = payload.get("document_ids")
    max_attempts = payload.get("max_attempts", 2)

    try:
        initial_state: RAGState = {
            "query": query_text.strip(),
            "original_query": query_text.strip(),
            "subject_list": raw_subject_list,
            "history": history,
            "match_count": match_count,
            "rerank": rerank,
            "dense_weight": dense_weight,
            "sparse_weight": sparse_weight,
            "document_ids": document_ids,
            "attempt_count": 0,
            "max_attempts": max_attempts,
        }

        result = query_graph.invoke(initial_state)

        return jsonify({
            "query": result.get("query"),
            "original_query": result.get("original_query"),
            "route": result.get("route"),
            "answer": result.get("answer"),
            "documents": result.get("documents", []),
            "sources": result.get("sources", []),
            "evaluation": result.get("evaluation"),
            "sufficient": result.get("sufficient"),
            "attempt_count": result.get("attempt_count", 0),
        }), 200

    except Exception as e:
        logger.exception("Error executing orchestrated query:")
        return jsonify({"detail": f"Query orchestration failed: {e}"}), 500

@ingest.route("/chat", methods=["POST"])
def chat():

    payload = request.get_json(silent=True) or {}
    message = payload.get("message") or payload.get("query")
    history = payload.get("history", [])

    if not isinstance(message, str) or not message.strip():
        return jsonify({"detail": "A non-empty message is required."}), 400
    if not isinstance(history, list):
        return jsonify({"detail": "History must be a list."}), 400
    raw_subject_list = []
    try:
        client = get_supabase_client()
        raw_subject_list = get_subjects(client)  # Retrieve subjects for the current user
    except Exception as e:
        logger.warning(f"Could not retrieve subjects for chat: {e}")

    # Optional retrieval configuration from request body (with defaults)
    match_count = payload.get("match_count")
    rerank = payload.get("rerank", False)
    dense_weight = payload.get("dense_weight", 1.5)
    sparse_weight = payload.get("sparse_weight", 0.5)
    document_ids = payload.get("document_ids")
    max_attempts = payload.get("max_attempts", 2)

    def generate() -> Iterator[str]:
        try:

            initial_state: RAGState = {
                "query": message.strip(),
                "original_query": message.strip(),
                "subject_list": raw_subject_list,
                "history": history,
                "match_count": match_count,
                "rerank": rerank,
                "dense_weight": dense_weight,
                "sparse_weight": sparse_weight,
                "document_ids": document_ids,
                "attempt_count": 0,
                "max_attempts": max_attempts,
            }

            result = query_graph.invoke(initial_state)

            if result.get("documents"):
                yield _sse({"type": "documents", "documents": result["documents"]})

            if result.get("sources"):
                yield _sse({"type": "sources", "sources": result["sources"]})

            answer = result.get("answer") or ""
            if answer:
                yield _sse({"type": "token", "content": answer})

            yield _sse({"type": "done"})

        except Exception as e:
            logger.exception("Error in chat orchestration:")
            yield _sse({"type": "error", "content": f"Unable to answer that question right now. {e}"})

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache"}
    )
