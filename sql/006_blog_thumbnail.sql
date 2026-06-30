-- Thumbnail ảnh cho blog (URL public từ bucket cms-media)
alter table public.blog_posts
  add column if not exists thumbnail_url text null;
