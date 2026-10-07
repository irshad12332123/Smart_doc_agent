-- Migration: Deterministic Document and Metadata Lookup Layer
-- Compatible with schema:
--   - subjects: id, semester_id, subject_code, name, created_at, subject_type, credits
--   - documents: id, title, description, document_type (enum), subject_id, uploaded_by, s3_key, mime_type, deadline, created_at, updated_at
--   - document_batches: document_id, batch_id, created_at
-- Adds optimized indexes and get_documents_by_filters RPC for deterministic retrieval.

-- 1. Ensure enum type document_type exists
do $$ begin
  create type public.document_type as enum (
    'notes', 'assignment', 'notice', 'syllabus', 'study_material', 'announcement', 'others', 'time_table'
  );
exception
  when duplicate_object then null;
end $$;

-- 2. Ensure columns and constraints on public.documents if not already present
alter table public.documents add column if not exists description text;
alter table public.documents add column if not exists document_type public.document_type;
alter table public.documents add column if not exists subject_id uuid references public.subjects(id) on delete set null;
alter table public.documents add column if not exists uploaded_by uuid references public.profiles(id) on delete set null;
alter table public.documents add column if not exists s3_key text;
alter table public.documents add column if not exists mime_type text;
alter table public.documents add column if not exists deadline timestamptz;
alter table public.documents add column if not exists updated_at timestamptz default now();

-- 3. Composite and single-column indexes for fast deterministic lookup and filtering
create index if not exists documents_subject_doc_type_idx
  on public.documents (subject_id, document_type);

create index if not exists documents_deadline_idx
  on public.documents (deadline)
  where deadline is not null;

create index if not exists documents_created_at_desc_idx
  on public.documents (created_at desc);

create index if not exists document_batches_doc_batch_idx
  on public.document_batches (document_id, batch_id);

-- GIN index on title and description for fast full-text keyword search
create index if not exists documents_fts_idx
  on public.documents
  using gin (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, '')));

-- 4. Clean up any previous function overloads before recreation
drop function if exists public.get_documents_by_filters(uuid, text, text, timestamptz, timestamptz, timestamptz, timestamptz, integer);
drop function if exists public.get_documents_by_filters(uuid, text, text, timestamptz, timestamptz, timestamptz, timestamptz, integer, uuid);
drop function if exists public.get_documents_by_filters;

-- 5. Deterministic Document Lookup RPC
create or replace function public.get_documents_by_filters(
  p_subject_id uuid default null,
  p_document_type text default null,
  p_search_query text default null,
  p_deadline_start timestamptz default null,
  p_deadline_end timestamptz default null,
  p_created_after timestamptz default null,
  p_created_before timestamptz default null,
  p_limit integer default 20,
  p_batch_id uuid default null
)
returns table (
  id uuid,
  title text,
  description text,
  document_type text,
  subject_id uuid,
  uploaded_by uuid,
  s3_key text,
  mime_type text,
  deadline timestamptz,
  created_at timestamptz,
  updated_at timestamptz,
  subject_name text,
  subject_code text
)
language sql
stable
security invoker
set search_path = public
as $$
  select
    d.id,
    d.title,
    d.description,
    d.document_type::text as document_type,
    d.subject_id,
    d.uploaded_by,
    d.s3_key,
    d.mime_type,
    d.deadline,
    d.created_at,
    coalesce(d.updated_at, d.created_at) as updated_at,
    s.name as subject_name,
    s.subject_code as subject_code
  from public.documents d
  left join public.subjects s on s.id = d.subject_id
  where
    (p_subject_id is null or d.subject_id = p_subject_id)
    and (
      p_batch_id is null
      or exists (
        select 1
        from public.document_batches db
        where db.document_id = d.id
          and db.batch_id = p_batch_id
      )
    )
    and (
      p_document_type is null
      or lower(d.document_type::text) = lower(trim(p_document_type))
      or (lower(trim(p_document_type)) in ('others', 'other') and lower(d.document_type::text) in ('others', 'other'))
      or (lower(trim(p_document_type)) in ('notice', 'announcement') and lower(d.document_type::text) in ('notice', 'announcement'))
      or (lower(trim(p_document_type)) in ('notes', 'study_material') and lower(d.document_type::text) in ('notes', 'study_material'))
    )
    and (p_deadline_start is null or d.deadline >= p_deadline_start)
    and (p_deadline_end is null or d.deadline <= p_deadline_end)
    and (p_created_after is null or d.created_at >= p_created_after)
    and (p_created_before is null or d.created_at <= p_created_before)
    and (
      p_search_query is null
      or trim(p_search_query) = ''
      or to_tsvector('english', coalesce(d.title, '') || ' ' || coalesce(d.description, '')) @@ plainto_tsquery('english', p_search_query)
      or d.title ilike ('%' || trim(p_search_query) || '%')
      or coalesce(d.description, '') ilike ('%' || trim(p_search_query) || '%')
    )
  order by
    case
      when p_search_query is not null and trim(p_search_query) <> '' then
        ts_rank_cd(to_tsvector('english', coalesce(d.title, '') || ' ' || coalesce(d.description, '')), plainto_tsquery('english', p_search_query))
      else 0.0
    end desc,
    coalesce(d.deadline, d.created_at) desc,
    d.created_at desc
  limit coalesce(p_limit, 20);
$$;

grant execute on function public.get_documents_by_filters to authenticated, service_role, anon;
