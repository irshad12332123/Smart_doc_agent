
def update_job(job_id,  supabase_client, **fields):
    if supabase_client is None:
        from backend.rag.lib.supabase import get_supabase_client
        supabase_client = get_supabase_client()

    """Persist job state in Supabase."""
    supabase_client.table("ingestion_jobs").update(fields).eq(
        "id", job_id
    ).execute()
