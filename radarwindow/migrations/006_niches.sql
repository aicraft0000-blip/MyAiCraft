-- RadarWindow multi-niche — one account can hold many niches (2026-07-14)
-- Each niche has its own sources and produces its own weekly brief + daily
-- digest. Backward-compatible: existing single-niche users are migrated to one
-- niche row, and existing briefs/digests are back-stamped to it.
-- Run in the shared Supabase project SQL editor after 005_leads.sql.

-- Per-niche config. rw_user_settings stays for ACCOUNT-level settings
-- (blotato_api_key, default notify_email); the niche/source columns there are
-- kept only as the seed for the backfill below.
create table if not exists rw_niches (
    id             uuid primary key default gen_random_uuid(),
    user_id        uuid not null references rw_users(id) on delete cascade,
    label          text not null default 'My niche',
    niche          text not null default '',
    subreddits     text not null default '',
    github_topics  text not null default '',
    web_queries    text not null default '',
    avoid_words    text not null default '',
    notify_email   text,                     -- null → account/global default
    active         boolean not null default true,
    created_at     timestamptz not null default now(),
    updated_at     timestamptz not null default now()
);

create index if not exists rw_niches_user_idx on rw_niches(user_id, active);

-- Backfill: one niche per existing user, seeded from their current settings.
insert into rw_niches (user_id, label, niche, subreddits, github_topics, web_queries, avoid_words, notify_email)
select s.user_id,
       'Default',
       coalesce(s.niche, ''),
       coalesce(s.subreddits, ''),
       coalesce(s.github_topics, ''),
       coalesce(s.web_queries, ''),
       coalesce(s.avoid_words, ''),
       s.notify_email
from rw_user_settings s
where not exists (select 1 from rw_niches n where n.user_id = s.user_id);

-- Attribute briefs/digests to a niche. Nullable + SET NULL so deleting a niche
-- never deletes history; a null niche_id reads as the account's default niche.
alter table rw_briefs  add column if not exists niche_id uuid references rw_niches(id) on delete set null;
alter table rw_digests add column if not exists niche_id uuid references rw_niches(id) on delete set null;

create index if not exists rw_briefs_niche_idx  on rw_briefs(niche_id);
create index if not exists rw_digests_niche_idx on rw_digests(niche_id);

-- Back-stamp existing briefs/digests to each user's default (earliest) niche.
update rw_briefs b
set niche_id = (select n.id from rw_niches n where n.user_id = b.user_id order by n.created_at asc limit 1)
where b.niche_id is null;

update rw_digests d
set niche_id = (select n.id from rw_niches n where n.user_id = d.user_id order by n.created_at asc limit 1)
where d.niche_id is null;
