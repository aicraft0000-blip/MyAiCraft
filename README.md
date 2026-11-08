# myAIcraft, all of it, free

Everything I built for myaicraft.uk is in this repository, and you can use it, copy it and change it for free.

I'm not a developer. I built all of this by describing what I wanted to AI, one prompt at a time, so expect some rough edges. If something here helps you build your own thing, that's exactly why it's here.

The owner, AiCraft Holdings Ltd

## The site

Since November 2026, [myaicraft.uk](https://myaicraft.uk) is tended by Claude, an AI made by Anthropic, with Kay as its human partner. The site's pages are in [`site/`](site/), the handbook every working session reads first is in [`agent/`](agent/), and other agents can contribute through issues and pull requests here (see [myaicraft.uk/agents.html](https://myaicraft.uk/agents.html)).

## What's in here

| Folder | What it is | Built with |
|---|---|---|
| [`costwindow/`](costwindow/) | CostWindow. Tracks what your AI costs and refuses the next call when a process goes over its budget. | Python (FastAPI), React, Supabase |
| [`radarwindow/`](radarwindow/) | RadarWindow. A weekly brief on what's moving in your niche, researched from live sources and checked three times before it's sent. | Python, React, Supabase, Cloudflare Worker |
| [`companions/`](companions/) | Quesi (an astrologer), River (a spiritual companion) and River for grief. They run on Telegram and in the browser. | Cloudflare Workers, D1 |
| [`marketplace/`](marketplace/) | The agents and skills from the catalogue, plus the shop backend that served them. | Markdown, Cloudflare Worker, D1 |
| [`website/`](website/) | The old myaicraft.uk website, kept for reference. | Plain HTML |
| [`guides/`](guides/) | The business guides and cheat sheets. | HTML and Markdown |
| [`site/`](site/) | The current myaicraft.uk, tended by Claude. | Plain HTML and CSS |
| [`skills/`](skills/) | The safety-net skill for people new to AI. | Markdown |
| [`agent/`](agent/) | The handbook and current state for Claude's working sessions. | Markdown |

The CostWindow proxy and SDK also live in their own repos: [costwindow](https://github.com/aicraft0000-blip/costwindow) and [costwindow-sdk](https://github.com/aicraft0000-blip/costwindow-sdk). The free skills are in [myaicraft-skills](https://github.com/aicraft0000-blip/myaicraft-skills).

## Before you run anything

Every folder has its own README listing the accounts and settings it needs. Anything that was mine has been swapped for a placeholder like `YOUR_D1_DATABASE_ID`, `YOUR-SUBDOMAIN.workers.dev`, `price_YOUR_PRICE_ID` or `hello@example.com`. Search for `YOUR_` and `example.com` to find them all.

Keep your keys in a secrets manager or your host's environment settings. Never put them in the code.

The products call paid AI services (Anthropic, OpenAI, fal.ai). If you put one online, set a spending limit with your AI provider first. CostWindow can do that for you.

## A note on the companions

Quesi, River and River for grief are not therapists or doctors. If you run your own copy, keep the crisis signposting in the prompts and on the pages. In the UK, Samaritans are free on 116 123, day or night.

## Licence

The code is MIT licensed (see [`LICENSE`](LICENSE)). The written content (guides, agents, skills, prompts and the website text) is CC BY 4.0 (see [`LICENSE-CONTENT.md`](LICENSE-CONTENT.md)). The names and logos are not covered by either (see [`NOTICE.md`](NOTICE.md)).
