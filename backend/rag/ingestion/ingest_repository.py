from datetime import datetime, timezone
from typing import Any, Optional


def _get_client(client: Optional[Any] = None) -> Any:
    if client is not None:
        return client
    try:
        from lib.supabase import get_supabase_client
        return get_supabase_client()
    except ImportError:
        from backend.rag.lib.supabase import get_supabase_client
        return get_supabase_client()


def _data(response: Any) -> list[dict[str, Any]]:
    result = getattr(response, "data", response)
    if isinstance(result, list):
        return result
    elif isinstance(result, dict):
        return [result]
    return []


def create_job(
    s3_key: str,
    file_sha256: str,
    document_id: Optional[str] = None,
    celery_task_id: Optional[str] = None,
    max_attempts: int = 5,
    supabase_client: Optional[Any] = None,
) -> dict[str, Any]:
    """Create a new record in ingestion_jobs."""
    client = _get_client(supabase_client)
    now = datetime.now(timezone.utc).isoformat()
    job_data: dict[str, Any] = {
        "s3_key": s3_key,
        "file_sha256": file_sha256,
        "status": "queued",
        "attempts": 0,
        "max_attempts": max_attempts,
        "created_at": now,
        "updated_at": now,
    }
    if document_id:
        job_data["document_id"] = document_id
    if celery_task_id:
        job_data["celery_task_id"] = celery_task_id

    res = client.table("ingestion_jobs").insert(job_data).execute()
    rows = _data(res)
    if not rows:
        raise RuntimeError("Failed to create ingestion job record")
    return rows[0]


def get_job(job_id: str, supabase_client: Optional[Any] = None) -> Optional[dict[str, Any]]:
    """Retrieve an ingestion job by ID."""
    client = _get_client(supabase_client)
    res = client.table("ingestion_jobs").select("*").eq("id", job_id).execute()
    rows = _data(res)
    return rows[0] if rows else None


def update_job(job_id: str, supabase_client: Optional[Any] = None, **fields) -> Optional[dict[str, Any]]:
    """Persist job state in Supabase."""
    client = _get_client(supabase_client)
    if "updated_at" not in fields:
        fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    res = client.table("ingestion_jobs").update(fields).eq("id", job_id).execute()
    rows = _data(res)
    return rows[0] if rows else None


def find_document_by_hash(file_sha256: str, supabase_client: Optional[Any] = None) -> Optional[dict[str, Any]]:
    """Check if a document with this hash_key already exists in public.documents."""
    client = _get_client(supabase_client)
    res = (
        client.table("documents")
        .select("id, title, s3_key, created_at, hash_key")
        .eq("hash_key", file_sha256)
        .limit(1)
        .execute()
    )
    rows = _data(res)
    return rows[0] if rows else None
