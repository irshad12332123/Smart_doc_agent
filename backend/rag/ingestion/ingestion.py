"""Core document-ingestion functions.

This module intentionally contains no Flask routes. HTTP parsing and response
formatting live in :mod:`ingestion.routes` so the ingestion workflow can also
be called from background jobs and tests without a request context.
"""

import hashlib
import logging
import mimetypes
import uuid
from typing import Any

from werkzeug.utils import secure_filename

from async_engine.tasks import process_ingestion_job
from config.settings import MAX_UPLOAD_BYTES, S3_BUCKET_NAME
from lib.aws_s3 import aws_s3_client
from utils.get_file_type import get_file_type

from .ingest_repository import create_job, find_document_by_hash, update_job

logger = logging.getLogger(__name__)


def _required_s3_bucket() -> str:
    if not S3_BUCKET_NAME:
        raise RuntimeError("S3_BUCKET_NAME must be configured")
    return S3_BUCKET_NAME


def ingest_files(
    files: list[Any],
    batch_ids: list[str],
    *,
    batch_id: str | None = None,
    subject_id: str | None = None,
    uploaded_by: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Upload files and queue their asynchronous ingestion jobs.

    The function accepts already-parsed upload objects and returns a response
    payload plus status code. Flask-specific request parsing stays in the route
    module.
    """
    if not files:
        return {"detail": "Attach at least one file in the 'files' field."}, 400

    if not batch_ids:
        return {"detail": "At least one batch is required."}, 400

    bucket = _required_s3_bucket()
    queued_jobs: list[dict[str, Any]] = []
    skipped_files: list[dict[str, Any]] = []

    try:
        for uploaded_file in files:
            filename = secure_filename(uploaded_file.filename or "")
            if not filename:
                logger.warning("File '%s' has an invalid name.", uploaded_file.filename)
                continue

            file_bytes: bytes = uploaded_file.read()
            if not file_bytes:
                raise ValueError(f"File '{filename}' is empty")

            if len(file_bytes) > MAX_UPLOAD_BYTES:
                raise ValueError(
                    f"File '{filename}' exceeds "
                    f"the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit"
                )

            file_sha256 = hashlib.sha256(file_bytes).hexdigest()
            existing_doc = find_document_by_hash(file_sha256)
            if existing_doc:
                logger.warning(
                    "File '%s' with hash %s already exists in documents table.",
                    filename,
                    file_sha256,
                )
                skipped_files.append(
                    {
                        "filename": filename,
                        "file_sha256": file_sha256,
                        "document_id": str(existing_doc.get("id")),
                        "reason": "already_exists",
                        "message": f"File '{filename}' has already been ingested.",
                    }
                )
                continue

            category = get_file_type(filename)
            s3_key = f"{category}/{uuid.uuid4().hex}_{filename}"
            content_type = (
                uploaded_file.mimetype
                or mimetypes.guess_type(filename)[0]
                or "application/octet-stream"
            )
            aws_s3_client.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=file_bytes,
                ContentType=content_type,
            )

            job_record = create_job(
                s3_key=s3_key,
                file_sha256=file_sha256,
                max_attempts=5,
            )
            job_id = job_record["id"]

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
                queued_jobs.append(
                    {
                        "job_id": job_id,
                        "task_id": task.id,
                        "filename": filename,
                        "status": "queued",
                        "s3_key": s3_key,
                        "file_sha256": file_sha256,
                        "doc_id": job_id,
                    }
                )
            except Exception as celery_err:
                logger.warning(
                    "Failed to enqueue Celery task for job %s: %s",
                    job_id,
                    celery_err,
                )
                update_job(
                    job_id,
                    status="enqueue_failed",
                    error=str(celery_err),
                    error_type=type(celery_err).__name__,
                )
                queued_jobs.append(
                    {
                        "job_id": job_id,
                        "task_id": None,
                        "filename": filename,
                        "status": "enqueue_failed",
                        "error": str(celery_err),
                        "s3_key": s3_key,
                        "file_sha256": file_sha256,
                        "doc_id": job_id,
                    }
                )

    except (RuntimeError, ValueError) as error:
        return {"detail": str(error)}, 400
    except Exception as error:
        logger.warning("Unexpected error during file ingestion enqueue: %s", error)
        return {
            "detail": "Document ingestion failed. Check the server logs.",
            "error": str(error),
        }, 500

    if skipped_files and not queued_jobs:
        return {
            "message": "All uploaded files have already been ingested.",
            "skipped": skipped_files,
            "jobs": [],
            "documents": [],
        }, 200

    return {
        "status": "queued",
        "message": f"Accepted: {len(queued_jobs)} document(s) queued for background ingestion.",
        "jobs": queued_jobs,
        "documents": queued_jobs,
        "skipped": skipped_files,
        "total_queued": len(queued_jobs),
        "total_skipped": len(skipped_files),
    }, 202
