-- CMS content tables for 9well.com static site build
-- Apply after sql/003_admin_user_role.sql

create table if not exists public.course_weeks (
  id uuid primary key default gen_random_uuid(),
  week_number integer not null unique check (week_number between 1 and 52),
  phase text not null,
  title text not null,
  goal text not null,
  sort_order integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz null
);

create table if not exists public.cms_lessons (
  id text primary key,
  week_number integer not null references public.course_weeks(week_number) on delete cascade,
  title text not null,
  lesson_type text not null check (lesson_type in ('video', 'baitap', 'checkin', 'doc')),
  duration text not null default '',
  body_html text not null default '',
  video_youtube text null,
  video_url text null,
  video_poster text null,
  free_trial boolean not null default false,
  published boolean not null default true,
  compliance_approved boolean not null default false,
  sort_order integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz null
);

create index if not exists cms_lessons_week_idx on public.cms_lessons (week_number, sort_order);

create table if not exists public.blog_posts (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  title text not null,
  category text not null default '',
  emoji text not null default '',
  excerpt text not null default '',
  read_time text not null default '',
  author text not null default '',
  body_html text not null default '',
  seo_description text not null default '',
  og_title text null,
  published boolean not null default true,
  published_at timestamptz null,
  sort_order integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz null
);

create table if not exists public.pricing_plans (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name text not null,
  price_vnd integer not null,
  price_label text not null default '/ một lần',
  role_description text not null default '',
  features jsonb not null default '[]'::jsonb,
  featured boolean not null default false,
  tag text null,
  cta_text text not null default 'Tư vấn qua Zalo',
  sort_order integer not null default 0,
  published boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz null
);

create table if not exists public.cms_faqs (
  id uuid primary key default gen_random_uuid(),
  question text not null,
  answer text not null,
  sort_order integer not null default 0,
  published boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz null
);

create table if not exists public.cms_timeline_blocks (
  id uuid primary key default gen_random_uuid(),
  week_range text not null,
  title text not null,
  description text not null,
  sort_order integer not null default 0,
  published boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz null
);

create table if not exists public.site_settings (
  key text primary key,
  value jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists public.publish_logs (
  id uuid primary key default gen_random_uuid(),
  triggered_by uuid null references public.users(id) on delete set null,
  status text not null check (status in ('pending', 'success', 'failed')),
  message text null,
  created_at timestamptz not null default now()
);
