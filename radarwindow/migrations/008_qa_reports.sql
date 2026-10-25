-- RadarWindow self-QA reports (2026-08-23)
-- The weekly alignment check (radarwindow.main --job=qa) writes one row per
-- active niche per run: settings lint findings (with auto-fixes noted), feed
-- health, and the on-niche fraction of the latest digest. The dashboard shows
-- the latest run as a notification.
-- Run in the shared Supabase project SQL editor after 007_rss_feeds.sql.

create table if not exists rw_qa_reports (
    id            uuid primary key default gen_random_uuid(),
    user_id       uuid not null references rw_users(id) on delete cascade,
    niche_id      uuid references rw_niches(id) on delete set null,
    status        text not null default 'ok',      -- ok | attention
    on_niche_pct  numeric,                          -- null when no digest to judge
    findings      jsonb not null default '[]'::jsonb,
    summary       text not null default '',
    created_at    timestamptz not null default now()
);

create index if not exists rw_qa_reports_user_created
    on rw_qa_reports (user_id, created_at desc);
