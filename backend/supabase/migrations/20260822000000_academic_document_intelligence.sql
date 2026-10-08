-- Academic scope and document metadata.  All changes are additive so the
-- existing ingestion tables and registry workflow remain intact.

create table if not exists public.courses (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.semesters (
  id uuid primary key default gen_random_uuid(),
  course_id uuid not null references public.courses(id) on delete cascade,
  number integer not null check (number > 0),
  created_at timestamptz not null default now(),
  unique (course_id, number)
);

create table if not exists public.batches (
  id uuid primary key default gen_random_uuid(),
  course_id uuid not null references public.courses(id) on delete restrict,
  code text not null unique,
  academic_session text not null,
  current_semester_id uuid references public.semesters(id) on delete set null,
  created_at timestamptz not null default now()
);

create table if not exists public.subjects (
  id uuid primary key default gen_random_uuid(),
  course_id uuid not null references public.courses(id) on delete cascade,
  semester_id uuid not null references public.semesters(id) on delete cascade,
  code text not null,
  name text not null,
  created_at timestamptz not null default now(),
  unique (course_id, code)
);

create table if not exists public.batch_subjects (
  batch_id uuid not null references public.batches(id) on delete cascade,
  subject_id uuid not null references public.subjects(id) on delete cascade,
  primary key (batch_id, subject_id)
);

create table if not exists public.student_batch_memberships (
  student_id uuid not null references public.students(id) on delete cascade,
  batch_id uuid not null references public.batches(id) on delete cascade,
  semester_id uuid references public.semesters(id) on delete set null,
  is_current boolean not null default true,
  created_at timestamptz not null default now(),
  primary key (student_id, batch_id)
);

-- The pre-existing roles table intentionally remains the CR authority.
alter table public.student_batch_roles
  add constraint student_batch_roles_batch_id_fkey
  foreign key (batch_id) references public.batches(id) on delete cascade;

create table if not exists public.faculty_batch_assignments (
  id uuid primary key default gen_random_uuid(),
  faculty_id uuid not null references public.faculty(id) on delete cascade,
  batch_id uuid not null references public.batches(id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (faculty_id, batch_id)
);

create table if not exists public.faculty_subject_assignments (
  id uuid primary key default gen_random_uuid(),
  faculty_id uuid not null references public.faculty(id) on delete cascade,
  subject_id uuid not null references public.subjects(id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (faculty_id, subject_id)
);

alter table public.documents add column if not exists description text;
alter table public.documents add column if not exists document_type text;
alter table public.documents add column if not exists subject_id uuid references public.subjects(id) on delete set null;
alter table public.documents add column if not exists uploaded_by uuid references public.profiles(id) on delete set null;
alter table public.documents add column if not exists file_url text;
alter table public.documents add column if not exists mime_type text;
alter table public.documents add column if not exists deadline timestamptz;
alter table public.documents add column if not exists batch_id uuid references public.batches(id) on delete set null;
alter table public.documents add column if not exists semester_id uuid references public.semesters(id) on delete set null;
alter table public.documents add column if not exists course_id uuid references public.courses(id) on delete set null;

create index if not exists documents_academic_scope_idx on public.documents (course_id, semester_id, batch_id, subject_id, created_at desc);
create index if not exists documents_uploaded_by_idx on public.documents (uploaded_by, created_at desc);
create index if not exists student_memberships_batch_idx on public.student_batch_memberships (batch_id) where is_current;
create index if not exists faculty_batch_assignments_batch_idx on public.faculty_batch_assignments (batch_id, faculty_id);
create index if not exists faculty_subject_assignments_subject_idx on public.faculty_subject_assignments (subject_id, faculty_id);

-- Filtered retrieval accepts IDs selected by the server, never model-generated SQL.
create or replace function public.match_document_chunks_filtered(
  query_embedding vector,
  match_threshold float,
  match_count int,
  document_ids uuid[]
)
returns table (id uuid, document_id uuid, content text, similarity float, title text)
language sql stable
as $$
  select dc.id, dc.document_id, dc.content,
         1 - (dc.embedding <=> query_embedding) as similarity,
         d.title
  from public.document_chunks dc
  join public.documents d on d.id = dc.document_id
  where dc.document_id = any(document_ids)
    and 1 - (dc.embedding <=> query_embedding) > match_threshold
  order by dc.embedding <=> query_embedding
  limit match_count;
$$;
