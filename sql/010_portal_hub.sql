-- Portal + Hub upgrade (9well him v3)
-- Uses public.users (custom JWT auth), NOT auth.users

-- Hub blog columns
alter table public.blog_posts
  add column if not exists cat_key text check (cat_key is null or cat_key in (
    'co-the','luyen-tap','tam-ly','cap-doi','loi-song'
  )),
  add column if not exists read_min integer,
  add column if not exists featured boolean not null default false,
  add column if not exists tags text[] not null default '{}',
  add column if not exists reviewed text not null default '';

create index if not exists blog_posts_cat_key_idx on public.blog_posts (cat_key);
create index if not exists blog_posts_featured_idx on public.blog_posts (featured) where featured;

-- Portal profiles
create table if not exists public.portal_profiles (
  user_id uuid primary key references public.users(id) on delete cascade,
  nickname text not null,
  pin_hash text null,
  plan_code text not null default 'none',
  program_started_at date null,
  current_week integer not null default 1 check (current_week between 1 and 8),
  week_done jsonb not null default '{}'::jsonb,
  privacy jsonb not null default '{"panicUrl":"https://www.google.com","disguise":false}'::jsonb,
  client_code text not null default '',
  trainer_stats jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz null
);

create table if not exists public.portal_quiz_results (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  answers jsonb not null,
  score integer not null,
  score_max integer not null,
  profile_text text not null,
  recommended_plan text not null,
  created_at timestamptz not null default now()
);

create index if not exists portal_quiz_user_idx on public.portal_quiz_results (user_id, created_at desc);

create table if not exists public.portal_checkins (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  week_number integer not null,
  mood text null,
  freq text null,
  control text null,
  notes text null,
  created_at timestamptz not null default now()
);

create index if not exists portal_checkins_user_idx on public.portal_checkins (user_id, created_at desc);

-- Lesson metadata for portal week actions
alter table public.cms_lessons
  add column if not exists week_actions text[] not null default '{}';

-- Optional landing CMS blocks
create table if not exists public.cms_landing_blocks (
  id text primary key,
  content jsonb not null default '{}'::jsonb,
  published boolean not null default true,
  updated_at timestamptz null
);

-- Portal config stored in site_settings
insert into public.site_settings (key, value) values
  ('portal_config', '{
    "zaloLink": "",
    "trainerUrl": "/trainer",
    "gameUrl": "/game",
    "hubUrl": "/blog",
    "sepay": {"bank": "Techcombank", "account": "1933 9999", "holder": "NGUYEN DINH DUONG", "qrImg": "/assets/payment/techcombank-qr.jpg"}
  }'::jsonb)
on conflict (key) do nothing;
