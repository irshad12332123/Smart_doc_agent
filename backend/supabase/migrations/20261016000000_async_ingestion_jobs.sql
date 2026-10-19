-- Migration: Asynchronous Ingestion Jobs and Document Hash Deduplication

-- 1. Ensure hash_key exists on public.documents
alter table public.documents add column if not exists hash_key text;
create index if not exists documents_hash_key_idx on public.documents (hash_key);

-- 2. Create ingestion_jobs table
create table if not exists public.ingestion_jobs (
  id uuid primary key default gen_random_uuid(),
  document_id uuid references public.documents(id) on delete set null,
  s3_key text not null,
  file_sha256 text not null,
  celery_task_id text unique,
  status text not null default 'queued' check (status in ('queued', 'processing', 'retrying', 'completed', 'failed', 'enqueue_failed', 'cancelled')),
  attempts integer not null default 0 check (attempts >= 0),
  max_attempts integer not null default 5 check (max_attempts > 0),
  error text,
  error_type text,
  result jsonb,
  started_at timestamptz,
  completed_at timestamptz,
  heartbeat_at timestamptz,
  next_retry_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Ensure document_id is nullable (it is populated after dense ingestion completes)
alter table public.ingestion_jobs alter column document_id drop not null;

-- 3. Indexes for fast query lookup
create index if not exists ingestion_jobs_status_idx on public.ingestion_jobs (status);
create index if not exists ingestion_jobs_file_sha256_idx on public.ingestion_jobs (file_sha256);
create index if not exists ingestion_jobs_celery_task_id_idx on public.ingestion_jobs (celery_task_id);
create index if not exists ingestion_jobs_created_at_desc_idx on public.ingestion_jobs (created_at desc);

-- 4. Enable Row Level Security and Policies
alter table public.ingestion_jobs enable row level security;

do $$ begin
  create policy "Allow authenticated read ingestion_jobs"
    on public.ingestion_jobs for select to authenticated using (true);
exception
  when duplicate_object then null;
end $$;

do $$ begin
  create policy "Allow service_role all on ingestion_jobs"
    on public.ingestion_jobs for all to service_role using (true) with check (true);
exception
  when duplicate_object then null;
end $$;
