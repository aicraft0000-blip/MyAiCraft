-- RadarWindow tables in shared Supabase project (public schema, rw_ prefix)
-- Run once via Supabase SQL editor

-- Users (mirrors Supabase auth.users)
create table if not exists rw_users (
    id          uuid primary key,  -- matches auth.users.id
    email       text not null unique,
    created_at  timestamptz not null default now()
);

-- Per-user niche + integration config
create table if not exists rw_user_settings (
    user_id             uuid primary key references rw_users(id) on delete cascade,
    niche               text not null default 'AI tools, independent builders, SaaS operators',
    subreddits          text not null default 'artificial,MachineLearning,LocalLLaMA,SideProject,indiehackers',
    github_topics       text not null default 'llm,anthropic,claude,mcp,ai-agents',
    web_queries         text not null default 'AI tools builders week,SaaS operator AI news,LLM pricing update',
    avoid_words         text not null default 'transformative,game-changing,revolutionary,unlock,empower,leverage',
    blotato_api_key     text,
    notify_email        text,
    updated_at          timestamptz not null default now()
);

create table if not exists rw_briefs (
    id                  uuid primary key default gen_random_uuid(),
    user_id             uuid not null references rw_users(id) on delete cascade,
    run_date            timestamptz not null default now(),
    content_md          text not null,
    signal_mood         text not null default 'neutral',
    status              text not null default 'draft'
                            check (status in ('draft', 'approved', 'posted', 'archived')),
    quality_score       numeric,
    revision_count      int not null default 0,
    niche_voice_passed  boolean not null default false,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);

create table if not exists rw_signals (
    id              uuid primary key default gen_random_uuid(),
    brief_id        uuid not null references rw_briefs(id) on delete cascade,
    source          text not null,
    title           text not null,
    url             text not null,
    raw_score       numeric not null,
    comment_count   int not null default 0,
    published_at    timestamptz,
    fetched_at      timestamptz not null default now(),
    volume_score    numeric not null,
    velocity_score  numeric not null,
    combined_score  numeric not null,
    metadata        jsonb not null default '{}'
);

create table if not exists rw_posts (
    id              uuid primary key default gen_random_uuid(),
    brief_id        uuid not null references rw_briefs(id) on delete cascade,
    platform        text not null check (platform in ('x', 'linkedin', 'instagram')),
    content         text not null,
    status          text not null default 'draft'
                        check (status in ('draft', 'scheduled', 'posted')),
    image_path      text,
    audio_path      text,
    video_path      text,
    image_public_url text,
    blotato_post_id text,
    scheduled_for   timestamptz,
    created_at      timestamptz not null default now()
);

create table if not exists rw_audit_log (
    id                  uuid primary key default gen_random_uuid(),
    brief_id            uuid not null references rw_briefs(id) on delete cascade,
    platform            text not null,
    action              text not null,
    blotato_response_id text,
    scheduled_for       timestamptz,
    created_at          timestamptz not null default now(),
    detail              jsonb not null default '{}'
);

create index if not exists rw_briefs_user_status_idx on rw_briefs(user_id, status);
create index if not exists rw_briefs_user_date_idx   on rw_briefs(user_id, run_date desc);
create index if not exists rw_posts_brief_idx         on rw_posts(brief_id);
create index if not exists rw_audit_brief_idx         on rw_audit_log(brief_id);
