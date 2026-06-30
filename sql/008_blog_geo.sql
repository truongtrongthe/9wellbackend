-- GEO fields for blog posts: key takeaways + per-article FAQ (JSON-LD)
alter table public.blog_posts
  add column if not exists key_takeaways jsonb not null default '[]'::jsonb,
  add column if not exists faq_items jsonb not null default '[]'::jsonb;

comment on column public.blog_posts.key_takeaways is 'Bullet ý chính đầu bài — mảng string cho GEO/AI';
comment on column public.blog_posts.faq_items is 'FAQ theo bài — mảng {question, answer} cho FAQPage JSON-LD';
