import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional
from dotenv import load_dotenv

# Ensure environment variables are loaded in Celery worker processes
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_RAG_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=_BACKEND_DIR / ".env")
load_dotenv(dotenv_path=_RAG_DIR / ".env")
load_dotenv()

from async_engine.celery_app import celery
from config.settings import S3_BUCKET_NAME
from ingestion.ingest_repository import get_job, update_job
from lib.aws_s3 import aws_s3_client
from services.ingestion.dense import DenseIngestion
from services.ingestion.sparse import SparseIngestion

logger = logging.getLogger(__name__)

@celery.task(
    bind=True,
    name="async_engine.tasks.process_ingestion_job",
    max_retries=5,
    default_retry_delay=10,
)
def process_ingestion_job(
    self,
    job_id: str,
    subject_id: Optional[str] = None,
    batch_ids: Optional[list[str]] = None,
    filename: Optional[str] = None,
    uploaded_by: Optional[str] = None,
) -> dict[str, Any]:
    """
    Asynchronously processes a document ingestion job:
    1. Updates job status to 'processing' and records attempt.
    2. Retrieves document bytes from S3 using the stored s3_key.
    3. Executes Dense Ingestion (extract text, chunk, embed, insert doc & chunks).
    4. Records the created document_id in ingestion_jobs.
    5. Executes Sparse Ingestion (regenerates BM25 index and chunk mapping).
    6. Updates job status to 'completed' with ingestion results.
    """
    now = datetime.now(timezone.utc).isoformat()
    logger.info(f"Starting async ingestion job {job_id} (Task ID: {self.request.id})")

    job = get_job(job_id)
    if not job:
        logger.error(f"Ingestion job {job_id} not found in database.")
        raise ValueError(f"Job {job_id} not found")

    attempts = (job.get("attempts") or 0) + 1
    max_attempts = job.get("max_attempts") or 5
    s3_key = job.get("s3_key")
    file_sha256 = job.get("file_sha256")

    # Update job state to processing
    started_at = job.get("started_at") or now
    update_job(
        job_id,
        status="processing",
        attempts=attempts,
        started_at=started_at,
        heartbeat_at=now,
        celery_task_id=self.request.id,
    )

    try:
        if not s3_key:
            raise ValueError(f"Job {job_id} has no s3_key associated")

        # 1. Fetch file bytes from S3
        bucket = S3_BUCKET_NAME
        if not bucket:
            raise RuntimeError("S3_BUCKET_NAME must be configured")

        logger.info(f"Downloading file from S3: {s3_key} in bucket {bucket}")
        s3_obj = aws_s3_client.get_object(Bucket=bucket, Key=s3_key)
        file_bytes: bytes = s3_obj["Body"].read()

        resolved_filename = filename or Path(s3_key).name
        extension = Path(resolved_filename).suffix.lower().lstrip(".")

        # 2. Dense Ingestion
        logger.info(f"Executing dense ingestion for job {job_id} ({resolved_filename})")
        dense_ingester = DenseIngestion()
        dense_result = dense_ingester.ingest(
            subject_id=subject_id,
            batch_ids=batch_ids or [],
            extension=extension,
            filename=resolved_filename,
            s3_key=s3_key,
            file_bytes=file_bytes,
            uploaded_by=uploaded_by,
            hash_key=file_sha256,
        )

        document_id = str(dense_result.get("doc_id") or "")
        now_heartbeat = datetime.now(timezone.utc).isoformat()
        update_job(
            job_id,
            document_id=document_id,
            heartbeat_at=now_heartbeat,
        )

        # 3. Sparse Ingestion (BM25 regeneration after dense ingestion)
        logger.info(f"Executing sparse ingestion sync for job {job_id}")
        sparse_ingester = SparseIngestion()
        sparse_result = sparse_ingester.regenerate_index()

        # 4. Mark completed
        completed_at = datetime.now(timezone.utc).isoformat()
        job_result = {
            "document_id": document_id,
            "filename": resolved_filename,
            "dense": dense_result,
            "sparse": sparse_result,
        }

        update_job(
            job_id,
            status="completed",
            completed_at=completed_at,
            heartbeat_at=completed_at,
            result=job_result,
            error=None,
            error_type=None,
        )

        logger.info(f"Ingestion job {job_id} successfully completed.")
        return job_result

    except Exception as exc:
        err_msg = str(exc)
        err_type = type(exc).__name__
        now_err = datetime.now(timezone.utc).isoformat()
        logger.error(f"Ingestion job {job_id} failed on attempt {attempts}/{max_attempts}: {err_msg}")

        if attempts < max_attempts:
            countdown = min(60, 5 * (2 ** (attempts - 1)))
            next_retry = datetime.now(timezone.utc) + timedelta(seconds=countdown)
            update_job(
                job_id,
                status="retrying",
                error=err_msg,
                error_type=err_type,
                heartbeat_at=now_err,
                next_retry_at=next_retry.isoformat(),
            )
            raise self.retry(exc=exc, countdown=countdown)
        else:
            update_job(
                job_id,
                status="failed",
                error=err_msg,
                error_type=err_type,
                completed_at=now_err,
                heartbeat_at=now_err,
            )
            raise exc


@celery.task(
    bind=True,
    name="async_engine.tasks.sync_sparse_index_task",
)
def sync_sparse_index_task(self) -> dict[str, Any]:
    """
    Asynchronously regenerates and synchronizes the sparse BM25 index from Supabase.
    """
    logger.info(f"Executing async sparse index sync task (Task ID: {self.request.id})")
    sparse_ingester = SparseIngestion()
    metadata = sparse_ingester.regenerate_index()
    logger.info("Async sparse index sync task completed successfully.")
    return metadata
