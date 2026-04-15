-- BOKUMO Supabase Schema
-- Supabase SQL Editor にコピペして Run する

-- UUID拡張
create extension if not exists "uuid-ossp";

-- プロフィール
create table profiles (
  id uuid references auth.users on delete cascade primary key,
  display_name text not null default '',
  avatar_url text,
  created_at timestamptz not null default now()
);

-- 口コミ
create table reviews (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references profiles(id) on delete cascade not null,
  shop_id integer not null,
  rating smallint not null check (rating >= 1 and rating <= 5),
  comment text not null default '',
  photos text[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index idx_reviews_shop_id on reviews(shop_id);
create index idx_reviews_user_id on reviews(user_id);
create unique index idx_reviews_user_shop on reviews(user_id, shop_id);

-- 口コミ集計
create table review_stats (
  shop_id integer primary key,
  avg_rating numeric(2,1) not null default 0,
  review_count integer not null default 0
);

-- お気に入り
create table favorites (
  user_id uuid references profiles(id) on delete cascade not null,
  shop_id integer not null,
  created_at timestamptz not null default now(),
  primary key (user_id, shop_id)
);
create index idx_favorites_user_id on favorites(user_id);

-- 店舗提案
create table shop_proposals (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references profiles(id) on delete cascade not null,
  name text not null,
  area text not null,
  address text not null default '',
  description text not null default '',
  reason text not null,
  status text not null default 'pending' check (status in ('pending','approved','rejected')),
  created_at timestamptz not null default now()
);

-- トリガー: ユーザー登録時にprofile自動作成
create or replace function handle_new_user()
returns trigger as $$
begin
  insert into profiles (id, display_name, avatar_url)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'name', ''),
    coalesce(new.raw_user_meta_data->>'avatar_url', '')
  );
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function handle_new_user();

-- トリガー: 口コミ変更時にreview_stats自動更新
create or replace function update_review_stats()
returns trigger as $$
declare
  target_shop_id integer;
begin
  target_shop_id := coalesce(new.shop_id, old.shop_id);
  insert into review_stats (shop_id, avg_rating, review_count)
  values (
    target_shop_id,
    (select coalesce(round(avg(rating)::numeric, 1), 0) from reviews where shop_id = target_shop_id),
    (select count(*) from reviews where shop_id = target_shop_id)
  )
  on conflict (shop_id) do update set
    avg_rating = excluded.avg_rating,
    review_count = excluded.review_count;
  return null;
end;
$$ language plpgsql security definer;

create trigger trg_review_stats
  after insert or update or delete on reviews
  for each row execute function update_review_stats();

-- RLS (Row Level Security)
alter table profiles enable row level security;
alter table reviews enable row level security;
alter table favorites enable row level security;
alter table shop_proposals enable row level security;
alter table review_stats enable row level security;

-- Profiles: 誰でも読める、本人のみ更新
create policy "profiles_select" on profiles for select using (true);
create policy "profiles_update" on profiles for update using (auth.uid() = id);

-- Reviews: 誰でも読める、認証ユーザーが投稿、本人のみ編集・削除
create policy "reviews_select" on reviews for select using (true);
create policy "reviews_insert" on reviews for insert with check (auth.uid() = user_id);
create policy "reviews_update" on reviews for update using (auth.uid() = user_id);
create policy "reviews_delete" on reviews for delete using (auth.uid() = user_id);

-- Favorites: 本人のみ
create policy "favorites_select" on favorites for select using (auth.uid() = user_id);
create policy "favorites_insert" on favorites for insert with check (auth.uid() = user_id);
create policy "favorites_delete" on favorites for delete using (auth.uid() = user_id);

-- Shop proposals: 誰でも読める、認証ユーザーが投稿
create policy "proposals_select" on shop_proposals for select using (true);
create policy "proposals_insert" on shop_proposals for insert with check (auth.uid() = user_id);

-- Review stats: 誰でも読める
create policy "review_stats_select" on review_stats for select using (true);

-- Storage: レビュー写真バケット
insert into storage.buckets (id, name, public) values ('review-photos', 'review-photos', true);

create policy "review_photos_select" on storage.objects for select using (bucket_id = 'review-photos');
create policy "review_photos_insert" on storage.objects for insert with check (
  bucket_id = 'review-photos' and auth.role() = 'authenticated'
);
create policy "review_photos_delete" on storage.objects for delete using (
  bucket_id = 'review-photos' and auth.uid()::text = (storage.foldername(name))[1]
);
