-- RadarWindow feedback loop: engagement data on posted content.
-- Run once via Supabase SQL editor (after 001_initial.sql).

create table if not exists rw_post_engagement (
    id              uuid primary key default gen_random_uuid(),
    post_id         uuid not null references rw_posts(id) on delete cascade,
    brief_id        uuid not null references rw_briefs(id) on delete cascade,
    user_id         uuid not null references rw_users(id) on delete cascade,
    platform        text not null,
    impressions     int  not null default 0,
    likes           int  not null default 0,
    comments        int  not null default 0,
    shares          int  not null default 0,
    clicks          int  not null default 0,
    -- engagement_rate = (likes+comments+shares+clicks) / max(impressions,1)
    engagement_rate numeric not null default 0,
    fetched_at      timestamptz not null default now()
);

create index if not exists rw_engagement_user_idx  on rw_post_engagement(user_id, fetched_at desc);
create index if not exists rw_engagement_brief_idx  on rw_post_engagement(brief_id);

-- Generated-media columns may already exist on rw_posts from 001; ensure present.
alter table rw_posts add column if not exists video_public_url text;
alter table rw_posts add column if not exists audio_public_url text;
