-- Learning roadmap: modules, per-user progress, notes, AI guidance.
-- Apply in Supabase SQL editor after sql/001_init.sql.

-- CATALOG (single linear track: unique sequence_order among active rows)
create table if not exists public.learning_modules (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  title text not null,
  description text null,
  sequence_order integer not null,
  status text not null default 'active' check (status in ('active', 'inactive')),
  created_at timestamptz not null default now(),
  updated_at timestamptz null
);

create unique index if not exists learning_modules_sequence_order_active_uidx
  on public.learning_modules (sequence_order)
  where status = 'active';

create index if not exists learning_modules_status_seq_idx
  on public.learning_modules (status, sequence_order);

-- PER-USER PROGRESS
create table if not exists public.user_module_progress (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  module_id uuid not null references public.learning_modules(id) on delete cascade,
  status text not null check (status in ('locked', 'in_progress', 'completed')),
  updated_at timestamptz not null default now(),
  unique (user_id, module_id)
);

create index if not exists user_module_progress_user_id_idx on public.user_module_progress (user_id);

-- NOTES
create table if not exists public.user_learning_notes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  content text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz null
);

create index if not exists user_learning_notes_user_created_idx
  on public.user_learning_notes (user_id, created_at desc);

-- AI GUIDANCE (latest row wins in app)
create table if not exists public.user_ai_guidance (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  message text not null,
  source text not null default 'system',
  created_at timestamptz not null default now()
);

create index if not exists user_ai_guidance_user_created_idx
  on public.user_ai_guidance (user_id, created_at desc);

-- Seed default modules (idempotent by code)
insert into public.learning_modules (code, title, description, sequence_order, status)
values
  (
    'foundation',
    'Nền tảng giao tiếp',
    'Communication foundation track.',
    1,
    'active'
  ),
  (
    'advanced_techniques',
    'Kỹ thuật tiên tiến',
    'Advanced techniques track.',
    2,
    'active'
  ),
  (
    'advanced_series',
    'Chuỗi nâng cao',
    'Advanced series; unlocks after prior modules.',
    3,
    'active'
  )
on conflict (code) do nothing;
