"""HTTP routes for document ingestion and indexing."""

import logging

from flask import Blueprint, g, jsonify, request

from async_engine.tasks import sync_sparse_index_task
from modules.auth.constants import AuthorizedRolesToAcessUpload
from modules.auth.middleware import require_role
from services.ingestion.sparse import SparseIngestion

from .ingest_repository import get_job
from .ingestion import ingest_files

logger = logging.getLogger(__name__)

ingest = Blueprint("ingest", __name__, url_prefix="/api")


@ingest.post("/ingest")
@require_role(*AuthorizedRolesToAcessUpload)
def ingest_route():
    """Accept files and queue their background ingestion jobs."""
    files = request.files.getlist("files")
    batch_ids = request.form.getlist("batch_ids")
    batch_id = request.form.get("batch_id") or request.form.get("batchId")
    if not batch_ids and batch_id:
        batch_ids = [batch_id]

    payload, status_code = ingest_files(
        files,
        batch_ids,
        batch_id=batch_id,
        subject_id=request.form.get("subject_id") or None,
        uploaded_by=getattr(getattr(g, "current_user", None), "id", None),
    )
    return jsonify(payload), status_code


@ingest.get("/jobs/<job_id>")
def get_job_status(job_id: str):
    """Retrieve status and metadata of an ingestion job."""
    try:
        job = get_job(job_id)
        if not job:
            return jsonify({"detail": f"Job {job_id} not found"}), 404
        return jsonify({"job": job}), 200
    except Exception as error:
        return jsonify({"detail": f"Failed to get job status: {error}"}), 500


@ingest.post("/index/sync")
def sync_index():
    """Queue BM25 sparse-index regeneration, with a synchronous fallback."""
    try:
        task = sync_sparse_index_task.delay()
        return jsonify(
            {
                "status": "queued",
                "message": "Sparse index regeneration queued asynchronously",
                "task_id": task.id,
            }
        ), 202
    except Exception as error:
        logger.warning(
            "Could not enqueue async sync index (%s). Running synchronous fallback.",
            error,
        )
        try:
            metadata = SparseIngestion().regenerate_index()
            return jsonify(
                {
                    "status": "success",
                    "message": "Sparse BM25 index regenerated synchronously",
                    "metadata": metadata,
                }
            ), 200
        except Exception as sync_error:
            return jsonify({"detail": f"Failed to sync sparse index: {sync_error}"}), 500
