-- CMS v3 content bundles (Learn / Shop / Hub videos / Trainer / Game / Portal / Landing / Legal)
-- Run: psql $DATABASE_URL -f sql/011_cms_v3_bundles.sql

create table if not exists public.cms_content_bundles (
  key text primary key,
  payload jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

comment on table public.cms_content_bundles is 'JSONB bundles for offline v3 modules; published to apps/web/public/v2/*.js';

-- Optional: last publish metadata
create table if not exists public.cms_publish_artifacts (
  id uuid primary key default gen_random_uuid(),
  triggered_by uuid null references public.users(id) on delete set null,
  files jsonb not null default '[]'::jsonb,
  message text null,
  created_at timestamptz not null default now()
);

-- Seed placeholder keys (empty); real seed via admin POST /bundles/seed or scripts/seed-cms-v3.mjs
insert into public.cms_content_bundles (key, payload) values
  ('learn_curriculum', '{}'::jsonb),
  ('shop_catalog', '{"disclaimer":"","cats":{},"products":[]}'::jsonb),
  ('hub_videos', '{"videos":[]}'::jsonb),
  ('hub_categories', '{"cats":{}}'::jsonb),
  ('trainer', '{}'::jsonb),
  ('game', '{}'::jsonb),
  ('portal_app', '{}'::jsonb),
  ('landing_copy', '{}'::jsonb),
  ('legal_pages', '{}'::jsonb)
on conflict (key) do nothing;
