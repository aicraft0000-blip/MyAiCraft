# RadarWindow

Researches what's moving in a niche (Reddit, Hacker News, GitHub, Polymarket and live news), scores it, writes a weekly brief, and checks the brief three times before it goes out. It can also build a media kit (posts, images, audio) from the brief.

## What's here

- `src/radarwindow/` is the pipeline: radar, scoring, synthesis, the quality gate, media and publishing.
- `web/backend/` is the API, `web/frontend/` the React app, `web/worker/` the Cloudflare Worker that serves the site and proxies `/api`.
- `migrations/` has the database schema to run in Supabase.

## What you need

- A Supabase project. Run the files in `migrations/` in order.
- `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`.
- Optional: `FAL_API_KEY` for images and audio, `MAILERSEND_API_KEY` and `MAILERSEND_FROM_EMAIL` for email, `NOTIFY_EMAIL` for where the brief is sent, `BLOTATO_API_KEY` and the `BLOTATO_*_ACCOUNT_ID` settings if you want it to post for you, `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` (it falls back to RSS without them).
- Your niche: `NICHE`, `WEB_SEARCH_QUERIES`, `REDDIT_SUBREDDITS`, `GITHUB_TOPICS`, and the `VISUAL_*` settings for the look of the images. Defaults are in `src/radarwindow/config.py`.

## Run it

```bash
pip install -e .
pytest
cd web/frontend && npm install && npm run dev
```

The `Dockerfile` builds the backend as a single container. The scheduled jobs (daily digest, Monday brief) run inside that container when `RUN_SCHEDULER=1`.
