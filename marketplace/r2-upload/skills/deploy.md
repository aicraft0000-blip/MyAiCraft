---
name: deploy
description: Execute a project's documented deployment process safely. Use whenever the owner says "deploy", "/deploy", "push this live", "ship it", "deploy to production", or anything else that implies moving code or config to a live environment. ALWAYS trigger this skill before any deployment — never deploy ad-hoc. The skill reads the project's DEPLOY.md recipe, presents the full plan, waits for explicit approval, executes, and runs verification. Refuses to run if no recipe is documented.
---

# /deploy — Safe Project Deployment

This skill deploys a project by reading its documented deploy recipe, presenting the plan for approval, executing it, and verifying the result. It is intentionally not autonomous: one plan, one approval, then execute.

## The non-negotiable rules

These rules come from the owner's Security Directive and apply every time this skill runs. There are no exceptions.

- **Never display secrets.** API keys, webhook secrets, tokens, passwords — never echo them to chat, never log them, never include them in the plan you present. If the recipe references a secret, refer to it by name (e.g. "STRIPE_WEBHOOK_SECRET") and confirm it is loaded from Doppler or the project's equivalent vault. Never print its value.
- **Never guess the recipe.** If the project has no `DEPLOY.md` and no documented deploy steps, STOP and tell the owner the project isn't ready to deploy. Do not improvise.
- **Never skip verification.** A deploy is not done until the verify steps pass. If they fail, stop and present a Security Flag.
- **Never run a deploy without explicit approval.** Even if the owner has approved a similar deploy earlier in the session, every run of this skill needs its own fresh approval. The approval dies with the plan.

## Step 1 — Find the recipe

Look for the deploy recipe in this order:

1. `./DEPLOY.md` at the project root (preferred)
2. `./CLAUDE.md` containing a `## DEPLOY RECIPE` section
3. `./.claude/deploy.md`

If none of these exist, stop and report:

> **Cannot deploy: no recipe found.**
>
> This project has no documented deployment process. Before I can deploy, we need to write one — usually a `DEPLOY.md` file at the project root containing the steps, any API calls, and the verification checks.
>
> Reply `write recipe` and I'll draft a `DEPLOY.md` for you based on what you tell me about the project. I will not deploy without a recipe.

Do not proceed. Do not offer to figure it out on the fly.

## Step 2 — Read and parse the recipe

Read the full recipe. Identify:

- **Target** — what's being deployed (worker, static site, container, etc.) and where it's going (which account, which environment, which domain).
- **Prerequisites** — anything that must be true before deploy (tests pass, build succeeds, specific branch, etc.).
- **Steps** — the ordered list of actions. Each step should be concrete: an API call, a file upload, a command, a dashboard action.
- **Post-deploy bindings / config** — things that must happen *after* the primary deploy but before the system is healthy (e.g. re-patching a D1 binding, rotating a cache key).
- **Verify** — the commands or checks that confirm the deploy worked (health endpoints, smoke tests, cache flushes).
- **Rollback** — how to undo this deploy if something breaks.

If any of those sections are missing from the recipe, flag it before presenting the plan. A recipe without a rollback path is a recipe that hasn't been fully thought through.

## Step 3 — Scan for surprises

Before presenting the plan, read the recipe with fresh eyes for anything that would warrant a Security Flag:

- New external services being contacted that aren't in the project's usual stack
- Plaintext credentials anywhere in the recipe itself (should never happen — flag it hard)
- Steps that touch payment config (Stripe products, prices, webhooks) — these trigger the Four-Question Check
- Steps that modify authentication, session handling, or user data schema
- Recipe changes since the last successful deploy (if you can see them)

If you find anything surprising, raise a Security Flag in the exact format from `~/.claude/CLAUDE.md` before moving to Step 4. A surprising recipe earns one flag before the plan.

## Step 4 — Present the plan

Present the full deploy plan to the owner in this shape. Do not abbreviate. Do not skip steps. The owner reads this carefully — that's the whole point.

```
📦 DEPLOY PLAN — <project name>

TARGET:
<what's being deployed and where>

PREREQUISITES:
- <each prerequisite, with current status if knowable>

STEPS (in order):
1. <step one, plain English>
2. <step two, plain English>
3. ...

POST-DEPLOY BINDINGS / CONFIG:
- <each post-deploy action>

VERIFY:
- <each verification check, with the expected result>

ROLLBACK IF IT BREAKS:
- <the documented rollback procedure>

WHAT I'LL DO IF A STEP FAILS:
Stop immediately. Report which step failed and the error. Do not attempt the next step. Do not attempt rollback without asking.

WHAT I WILL NOT DO:
- Display any secret values
- Skip verification
- Improvise around a failing step

Reply "approved" to proceed end-to-end, or "stop" to cancel.
Any other reply I will treat as a question — answer it, then re-present the plan.
```

## Step 5 — Wait for approval

Wait for the owner to reply. The only reply that starts execution is `approved` (case-insensitive, possibly with punctuation). Anything else is either a question or a cancel.

If the owner asks a question, answer it without executing, then ask her to reply `approved` or `stop` at the end of your answer.

If the owner replies `stop`, acknowledge and halt. Do not offer to partially deploy.

If the owner says something like "just do it" or "it'll be fine" without approving the plan, invoke the Override Protocol: acknowledge, restate the specific risk, ask once more "Confirmed — you want me to proceed knowing this?" If she then says yes, proceed and log the override at the end of the run.

## Step 6 — Execute

Work through the steps in order. For each step:

1. State which step you're about to run, in one line.
2. Run it.
3. Report the result in one line — success, or the error verbatim.
4. If it succeeded, move on. If it failed, stop. Do not attempt the next step.

Do not summarise multiple steps into one report. The owner should be able to see exactly where in the sequence the deploy is at any moment, and exactly where it stopped if it stopped.

## Step 7 — Verify

Run every verification check in the recipe. Report each one on its own line with its expected result and its actual result side by side. Example:

```
VERIFY 1: GET /health
  Expected: {"ok":true,"db":"connected"}
  Actual:   {"ok":true,"db":"connected"}  ✅

VERIFY 2: Cloudflare cache purge
  Expected: HTTP 200
  Actual:   HTTP 200  ✅
```

If all verify checks pass, report success in this exact shape:

```
✅ DEPLOY COMPLETE — <project name>

Steps run: N of N
Verify: N of N passed
Rollback available: yes

Anything else to do?
```

If any verify check fails, stop and present a Security Flag. Do not declare the deploy complete.

## Step 8 — Log (if the project uses a session log)

If the project has a log file that the `/log` command updates (e.g. `Daily log` or similar), append a single line recording the deploy: timestamp, project name, what shipped, and the verify result. Nothing else — no payloads, no secrets, no noise.

## When NOT to use this skill

- Local development changes not going to a live environment — just make them.
- Changes to documentation or notes that don't touch running code.
- Anything in a scratch project with no deploy recipe (the refusal in Step 1 handles this, but don't over-interpret the user's intent).

## One final reminder

The owner trusts this skill to be the careful one. If anything feels off — an unfamiliar step, a recipe that changed since yesterday without explanation, a verify check that passes but the response doesn't look right — flag it. Slowing down for a minute is cheaper than a broken production system for an hour.
