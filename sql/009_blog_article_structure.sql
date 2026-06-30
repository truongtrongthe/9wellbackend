-- Structured article blocks for full blog template (TOC, summary, related, etc.)
alter table public.blog_posts
  add column if not exists toc_items jsonb not null default '[]'::jsonb,
  add column if not exists summary_quick text not null default '',
  add column if not exists action_box jsonb not null default '{}'::jsonb,
  add column if not exists author_bio text not null default '',
  add column if not exists author_initials text not null default '',
  add column if not exists related_slugs text[] not null default '{}',
  add column if not exists show_sticky_cta boolean not null default true,
  add column if not exists hero_image_url text null;

comment on column public.blog_posts.toc_items is 'Mục lục — mảng {id, label}';
comment on column public.blog_posts.summary_quick is 'Tóm tắt nhanh — đoạn văn đầu bài';
comment on column public.blog_posts.action_box is 'Khối hành động — {title, body}';
comment on column public.blog_posts.author_bio is 'Bio tác giả cho author-box';
comment on column public.blog_posts.author_initials is 'Chữ viết tắt avatar author-box';
comment on column public.blog_posts.related_slugs is 'Slug bài viết liên quan (Đọc tiếp)';
comment on column public.blog_posts.show_sticky_cta is 'Hiện sticky CTA cuối trang';
comment on column public.blog_posts.hero_image_url is 'Ảnh hero đầu bài; fallback thumbnail_url';
