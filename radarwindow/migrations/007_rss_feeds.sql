-- RadarWindow custom RSS feeds per niche (2026-08-11)
-- Lets a niche watch any site that publishes a feed (blogs, newsletters,
-- YouTube channels, news sites) alongside the built-in sources.
-- Comma-separated feed URLs, same convention as subreddits/web_queries.
-- Run in the shared Supabase project SQL editor after 006_niches.sql,
-- BEFORE deploying the backend that selects this column.

alter table rw_niches add column if not exists rss_feeds text not null default '';
