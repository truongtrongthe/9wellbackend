-- Allow bank-transfer payments + seed membership packages used by Learn checkout.

alter table public.payments drop constraint if exists payments_provider_check;
alter table public.payments
  add constraint payments_provider_check check (provider in ('momo', 'bank'));

insert into public.membership_packages (code, name, description, price_vnd, duration_days, status, sort_order)
values
  ('start', 'Khởi đầu', 'Chẩn đoán + lộ trình tự tập tuần 1–4', 390000, 120, 'active', 10),
  ('core', 'Đồng hành', 'Full 8 tuần + check-in 1-1 nhẹ', 1990000, 180, 'active', 20),
  ('deep', 'Chuyên sâu', 'Coaching 1-1 sát + module bạn đời', 3990000, 365, 'active', 30)
on conflict (code) do update set
  name = excluded.name,
  description = excluded.description,
  price_vnd = excluded.price_vnd,
  duration_days = excluded.duration_days,
  status = excluded.status,
  sort_order = excluded.sort_order,
  updated_at = now();

-- Ensure intro lesson is free_trial (prefer w1l1)
update public.cms_lessons set free_trial = false where free_trial = true;
update public.cms_lessons set free_trial = true where id = 'w1l1';
