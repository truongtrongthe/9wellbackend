-- Admin role on users (JWT-based admin). Apply after sql/001_init.sql.

alter table public.users
  add column if not exists role text not null default 'user';

comment on column public.users.role is 'user | admin — admin may call /admin/* with Bearer JWT.';
