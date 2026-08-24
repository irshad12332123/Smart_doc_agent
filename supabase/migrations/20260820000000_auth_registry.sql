-- Official eligibility registry and safe account-linking workflow.
-- Apply with the Supabase CLI/migration system before enabling /auth/register.

create type public.app_role as enum ('student', 'faculty', 'admin');

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null,
  role public.app_role not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.students (
  id uuid primary key default gen_random_uuid(),
  student_id text not null unique,
  registered_email text not null unique,
  name text not null,
  profile_id uuid unique references public.profiles(id) on delete set null,
  created_at timestamptz not null default now()
);

create table if not exists public.faculty (
  id uuid primary key default gen_random_uuid(),
  faculty_id text not null unique,
  registered_email text not null unique,
  name text not null,
  profile_id uuid unique references public.profiles(id) on delete set null,
  created_at timestamptz not null default now()
);

-- CR is a batch-scoped permission, not a global authentication role.
create table if not exists public.student_batch_roles (
  student_id uuid not null references public.students(id) on delete cascade,
  batch_id uuid not null,
  role text not null check (role in ('student', 'cr')),
  primary key (student_id, batch_id)
);

alter table public.profiles enable row level security;
alter table public.students enable row level security;
alter table public.faculty enable row level security;
alter table public.student_batch_roles enable row level security;

create policy "Users can read their own profile"
  on public.profiles for select to authenticated using (id = auth.uid());
create policy "Students can read their own registry record"
  on public.students for select to authenticated using (profile_id = auth.uid());
create policy "Faculty can read their own registry record"
  on public.faculty for select to authenticated using (profile_id = auth.uid());
create policy "Students can read their own batch roles"
  on public.student_batch_roles for select to authenticated
  using (exists (select 1 from public.students s where s.id = student_id and s.profile_id = auth.uid()));

-- This function is called only with the service-role key. FOR UPDATE makes
-- competing registrations deterministic, and the profile/link update commits
-- together. The role comes from the server, never from client JSON.
create or replace function public.complete_registry_registration(
  p_registry_type text,
  p_registry_id uuid,
  p_profile_id uuid,
  p_full_name text,
  p_role public.app_role
)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  linked_profile_id uuid;
begin
  if (p_registry_type = 'student' and p_role <> 'student')
     or (p_registry_type = 'faculty' and p_role <> 'faculty') then
    raise exception 'Invalid registry role pairing';
  end if;

  if p_registry_type = 'student' then
    select profile_id into linked_profile_id from public.students where id = p_registry_id for update;
  elsif p_registry_type = 'faculty' then
    select profile_id into linked_profile_id from public.faculty where id = p_registry_id for update;
  else
    raise exception 'Invalid registry type';
  end if;

  if not found then raise exception 'Registry record not found'; end if;
  if linked_profile_id is not null then raise exception 'Registry record already linked'; end if;

  insert into public.profiles (id, full_name, role) values (p_profile_id, p_full_name, p_role);
  if p_registry_type = 'student' then
    update public.students set profile_id = p_profile_id where id = p_registry_id;
  else
    update public.faculty set profile_id = p_profile_id where id = p_registry_id;
  end if;
end;
$$;

revoke all on function public.complete_registry_registration(text, uuid, uuid, text, public.app_role) from public, anon, authenticated;
grant execute on function public.complete_registry_registration(text, uuid, uuid, text, public.app_role) to service_role;
