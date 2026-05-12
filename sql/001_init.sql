-- 9wellbackend initial schema for Supabase Postgres
-- Apply in Supabase SQL editor.

create extension if not exists pgcrypto;

-- USERS
create table if not exists public.users (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  name text not null,
  phone text null,
  password_hash text null,
  provider text not null default 'email',
  email_verified boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz null
);

create index if not exists users_created_at_idx on public.users (created_at desc);

-- REFRESH TOKENS (hashed storage, rotated on refresh)
create table if not exists public.refresh_tokens (
  id text primary key,
  user_id uuid not null references public.users(id) on delete cascade,
  token_hash text not null unique,
  expires_at timestamptz not null,
  created_at timestamptz not null default now()
);

create index if not exists refresh_tokens_user_id_idx on public.refresh_tokens (user_id);
create index if not exists refresh_tokens_expires_at_idx on public.refresh_tokens (expires_at);

-- MEMBERSHIP PACKAGES (catalog)
create table if not exists public.membership_packages (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name text not null,
  description text null,
  price_vnd integer not null check (price_vnd >= 0),
  duration_days integer not null check (duration_days > 0),
  status text not null default 'active' check (status in ('active', 'inactive')),
  sort_order integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz null
);

create index if not exists membership_packages_status_sort_idx
  on public.membership_packages (status, sort_order, created_at desc);

-- SUBSCRIPTIONS (entitlement)
create table if not exists public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  package_id uuid not null references public.membership_packages(id),
  status text not null check (status in ('trial', 'active', 'expired', 'canceled')),
  current_period_start timestamptz not null,
  current_period_end timestamptz not null,
  auto_renew boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz null
);

create index if not exists subscriptions_user_id_idx on public.subscriptions (user_id);
create index if not exists subscriptions_status_idx on public.subscriptions (status);
create index if not exists subscriptions_period_end_idx on public.subscriptions (current_period_end);

-- Enforce at most one active subscription per user (optional but recommended)
create unique index if not exists subscriptions_one_active_per_user
  on public.subscriptions (user_id)
  where status in ('trial', 'active');

-- ORDERS
create table if not exists public.orders (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  package_id uuid not null references public.membership_packages(id),
  amount_vnd integer not null check (amount_vnd >= 0),
  currency text not null default 'VND',
  status text not null check (status in ('pending', 'paid', 'failed', 'canceled', 'expired')),
  idempotency_key text null unique,
  created_at timestamptz not null default now(),
  updated_at timestamptz null
);

create index if not exists orders_user_id_created_at_idx on public.orders (user_id, created_at desc);
create index if not exists orders_status_idx on public.orders (status);

-- PAYMENTS
create table if not exists public.payments (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references public.orders(id) on delete cascade,
  provider text not null check (provider in ('momo')),
  status text not null check (status in ('created', 'processing', 'succeeded', 'failed')),
  provider_payment_id text null,
  pay_url text null,
  deeplink text null,
  qr_code_url text null,
  raw_create_response jsonb null,
  raw_ipn_payload jsonb null,
  signature_valid boolean null,
  created_at timestamptz not null default now(),
  updated_at timestamptz null
);

create index if not exists payments_order_id_idx on public.payments (order_id);
create index if not exists payments_status_idx on public.payments (status);

