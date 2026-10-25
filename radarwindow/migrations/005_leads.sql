-- RadarWindow lead-finder — draft-and-queue (2026-07-14)
-- Public posts where someone voices a pain a product solves, plus a drafted,
-- helpful reply queued for MANUAL review. RadarWindow never sends these.
-- Run in the shared Supabase project SQL editor after 004_customers.sql.

create table if not exists rw_leads (
    id           uuid primary key default gen_random_uuid(),
    user_id      uuid not null references rw_users(id) on delete cascade,
    source       text not null,                 -- reddit | hackernews | websearch
    product      text not null,                 -- costwindow | radarwindow
    url          text not null,                 -- link to the thread to reply to
    title        text not null,
    excerpt      text not null default '',       -- the person's own words
    author       text,
    fit_score    numeric not null default 0,     -- 0–1 classifier confidence
    rationale    text not null default '',       -- one honest line on why it fits
    draft_reply  text not null default '',       -- helpful-first reply, posted by hand
    status       text not null default 'pending'
                     check (status in ('pending', 'approved', 'dismissed')),
    created_at   timestamptz not null default now(),
    unique (user_id, url)                        -- never double-queue a thread
);

create index if not exists rw_leads_user_status_idx
    on rw_leads(user_id, status, created_at desc);
