-- RadarWindow daily digests + public brief pages.
-- Run once via Supabase SQL editor (after 002_feedback.sql).

-- Daily signal digest: radar + scoring only, no LLM. One row per digest run.
create table if not exists rw_digests (
    id              uuid primary key default gen_random_uuid(),
    user_id         uuid references rw_users(id) on delete cascade,
    run_date        timestamptz not null default now(),
    content_md      text not null,
    signals         jsonb not null default '[]'::jsonb,
    source_health   jsonb,
    created_at      timestamptz not null default now()
);

create index if not exists rw_digests_user_date_idx on rw_digests(user_id, run_date desc);

-- Public brief pages: a brief can be published read-only at /p/<slug>.
alter table rw_briefs add column if not exists is_public boolean not null default false;
alter table rw_briefs add column if not exists public_slug text unique;

create index if not exists rw_briefs_public_idx on rw_briefs(is_public, run_date desc) where is_public;
