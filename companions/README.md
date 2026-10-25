# The companions: Quesi, River and River for grief

- **Quesi** is an astrologer. It works out your natal chart from your birth details and reads it alongside the live sky, drawing on Tropical astrology, Sabian symbols and Chinese astrology. `workers/quesi-backend.js`
- **River** is a spiritual companion for faith, doubt, ritual and meaning, from any tradition or none. `workers/river-backend.js`
- **River for grief** is a quieter version of River for people who are grieving. Its full prompt is in `GriefRiver-SOUL.md`, and it runs on the River worker.

Each one runs as a Cloudflare Worker with a D1 database, and talks to people on Telegram and on the web pages in `../website/`.

## What you need

- A Cloudflare account. Create a D1 database for each worker and put its ID in `workers/wrangler.quesi.toml` and `workers/wrangler.river.toml` (they say `YOUR_D1_DATABASE_ID`). The files in `workers/migrations/` add web chat and grief support to the River database. The original Quesi and River tables were set up by hand and their schema isn't in this repo yet, so you'll need to work them out from the queries in the workers.
- A Telegram bot for each, from @BotFather: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`.
- An AI key: `OPENAI_API_KEY` for Quesi, `ANTHROPIC_API_KEY` (and optionally `OPENAI_API_KEY`) for River.
- `OWNER_TELEGRAM_ID` (your own Telegram user ID) and `DEV_SECRET` or `ADMIN_SECRET` to unlock the owner-only routes. Without them those routes stay switched off.
- `SITE_URL`.
- Optional: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` and the `STRIPE_*_PRICE_ID` settings for paid plans, `MAILERSEND_*` for email, `COSTWINDOW_API_KEY` to track spend.

Set secrets with `wrangler secret put NAME --config workers/wrangler.quesi.toml` and deploy with `wrangler deploy --config workers/wrangler.quesi.toml` (same for River).

`docs/QUESI-ARCHITECTURE.md` explains how Quesi is put together.

## Please keep these safe

They are not therapists or doctors. If you run your own copy, keep the crisis signposting in the prompts and on the pages. In the UK, Samaritans are free on 116 123, day or night.
