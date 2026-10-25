# Agents and skills

These are the agents and skills from the myAIcraft catalogue. Each one is a Markdown file you can paste into Claude (as a project instruction, a skill, or at the start of a chat) or into any other AI assistant.

- `r2-upload/agents/` has the agents, many in a full and a compact edition.
- `r2-upload/skills/` has the skills.
- `*-Edition.md` in this folder are the full and compact editions of Chief of Staff, The Director and Vigil.

Some were written for my own setup, so read them through and change anything that mentions an owner, a tool or an account to fit yours.

## The shop backend

`workers/marketplace-backend.js` is the Cloudflare Worker that ran the shop: Stripe checkout, magic-link sign-in and downloads. You don't need it to use the agents and skills. If you want to run your own shop, it needs a D1 database (`workers/wrangler.marketplace.toml`, schema in `workers/migrations/` and `workers/seeds/`), an R2 bucket for the files (`MARKETPLACE_FILES`), `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `MAILERSEND_*`, `CHECKOUT_SUCCESS_URL` and `CHECKOUT_CANCEL_URL`.
