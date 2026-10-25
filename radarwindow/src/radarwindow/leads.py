from __future__ import annotations

import asyncio
import html as _html
import json
import logging
import re
from datetime import datetime, timezone

import anthropic
import httpx

from .config import settings
from .models import Lead, LeadStatus, SourceName
from .radar.reddit import search_reddit
from .synthesis import _load_json  # tolerant model-JSON parsing (same package util)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Product knowledge — what each product does and the pain it genuinely solves.
# The classifier uses "solves" to decide a real fit; the drafter uses "pitch"
# for the one honest, low-key mention (only when it fits). Keep these accurate:
# overclaiming here is what turns a helpful reply into spam.
# ---------------------------------------------------------------------------
PRODUCTS: dict[str, dict[str, str]] = {
    "costwindow": {
        "name": "CostWindow",
        "does": (
            "a drop-in proxy for Anthropic/OpenAI/Google LLM calls that tracks spend "
            "per process and has a HARD kill switch — it refuses calls once a budget "
            "is hit, before the provider is charged."
        ),
        "solves": (
            "someone scared of or burned by an unpredictable AI/agent bill; wanting a "
            "hard spend cap or kill switch on an autonomous agent or API key; an agent "
            "that ran too long and cost too much; needing to control LLM costs across "
            "providers without building it themselves."
        ),
        "pitch": (
            "I built CostWindow for exactly this — it's a drop-in proxy with a hard kill "
            "switch that stops the calls once you hit a budget, so an agent can't run "
            "past a cap. Free tier covers a couple of processes."
        ),
    },
    "radarwindow": {
        "name": "RadarWindow",
        "does": (
            "an intelligence pipeline that velocity-scores what's trending in a specific "
            "niche and writes a weekly analyst brief plus ready-to-post content for it."
        ),
        "solves": (
            "someone struggling to keep up with fast-moving news in their niche; needing "
            "a repeatable content pipeline; wanting trend/signal detection rather than "
            "manually trawling feeds."
        ),
        "pitch": (
            "I built RadarWindow for this — it watches a niche, scores what's actually "
            "accelerating, and writes the weekly brief so you're not trawling feeds by hand."
        ),
    },
}

_URL_RE = re.compile(r"https?://\S+")
_TAG_RE = re.compile(r"<[^>]+>")


def _focus_products() -> dict[str, dict[str, str]]:
    """The products the hunt is scoped to (LEADS_PRODUCTS, default: all known)."""
    wanted = [p.strip().lower() for p in settings.LEADS_PRODUCTS.split(",") if p.strip()]
    if not wanted:
        return PRODUCTS
    return {k: v for k, v in PRODUCTS.items() if k in wanted} or PRODUCTS


def _llm_client() -> anthropic.Anthropic:
    """Anthropic client for classify/draft, routed through the CostWindow proxy
    when configured — same dogfooding + hard kill switch as synthesis, tracked
    under its own process label so lead spend is separable from brief spend."""
    if settings.COSTWINDOW_PROXY_URL:
        return anthropic.Anthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            base_url=settings.COSTWINDOW_PROXY_URL,
            default_headers={"X-CostWindow-Label": settings.COSTWINDOW_LEADS_LABEL},
        )
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


# ---------------------------------------------------------------------------
# Candidate gathering — where the pain gets voiced (Reddit, HN, public web).
# Note: these are NOT Blotato platforms. Leads are found where people ask for
# help; replies are posted by hand, never auto-sent.
# ---------------------------------------------------------------------------
async def _reddit_candidates(client: httpx.AsyncClient, cfg: dict) -> list[dict]:
    return await search_reddit(
        client,
        subreddits=cfg["lead_subreddits"],
        queries=cfg["lead_queries"],
        per_query=settings.LEADS_PER_QUERY,
    )


async def _hn_candidates(client: httpx.AsyncClient, cfg: dict) -> list[dict]:
    """HN via Algolia (no auth). Comments matter most — that's where 'how do I
    stop my agent bill' questions get asked."""
    out: list[dict] = []
    seen: set[str] = set()
    for q in cfg["lead_queries"]:
        try:
            r = await client.get(
                "https://hn.algolia.com/api/v1/search_by_date",
                params={"query": q, "tags": "(story,comment)",
                        "hitsPerPage": settings.LEADS_PER_QUERY},
            )
            r.raise_for_status()
        except Exception as exc:
            log.warning("HN lead search q=%r failed: %s", q, exc)
            continue
        for hit in r.json().get("hits", []):
            oid = hit.get("objectID")
            if not oid or oid in seen:
                continue
            body = _TAG_RE.sub("", hit.get("comment_text") or hit.get("story_text") or "").strip()
            title = hit.get("title") or hit.get("story_title") or ""
            if not body and not title:
                continue
            seen.add(oid)
            out.append({
                "source": SourceName.HACKERNEWS.value,
                "title": title,
                "url": f"https://news.ycombinator.com/item?id={oid}",
                "body": body[:1200],
                "author": hit.get("author"),
                "matched_query": q,
            })
        await asyncio.sleep(0.2)
    log.info("HN lead search: %d candidate items", len(out))
    return out


def _web_candidates_blocking(cfg: dict) -> list[dict]:
    """Anthropic web_search to surface public posts (forums, Reddit threads,
    StackOverflow, X) where someone is currently asking about the pain. Direct
    Anthropic (parity with the brief's websearch — tool-use, not proxied)."""
    anth = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    pains = "; ".join(p["solves"] for p in _focus_products().values())
    prompt = (
        "Use web search to find PUBLIC posts by real people (Reddit threads, forums, "
        "Stack Overflow, X/Twitter, dev.to) asking for help with any of these problems, "
        "posted recently:\n\n"
        f"{pains}\n\n"
        "I want the actual thread where a person is asking — not articles, blog posts, "
        "product pages, or listicles. Only include a result if a real person is voicing "
        "the problem and could be replied to.\n\n"
        "Return ONLY a JSON array of up to 6 objects, each:\n"
        '{"title": str, "url": str (direct link to the post), '
        '"quote": str (the person\'s own words, verbatim), "author": str or null}\n'
        "No preamble, no markdown fences. Empty array if you find none."
    )
    r = anth.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=1500,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in r.content if getattr(b, "type", None) == "text").strip()
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        rows = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        log.warning("web lead search: could not parse model JSON")
        return []
    out = []
    for row in rows:
        url = (row.get("url") or "").strip()
        if not url.startswith("http"):
            continue
        out.append({
            "source": SourceName.WEBSEARCH.value,
            "title": (row.get("title") or "").strip(),
            "url": url,
            "body": (row.get("quote") or "").strip()[:1200],
            "author": row.get("author"),
            "matched_query": "web",
        })
    log.info("web lead search: %d candidate posts", len(out))
    return out


async def _gather_candidates(cfg: dict) -> list[dict]:
    async with httpx.AsyncClient(timeout=30) as client:
        results = await asyncio.gather(
            _reddit_candidates(client, cfg),
            _hn_candidates(client, cfg),
            asyncio.to_thread(_web_candidates_blocking, cfg),
            return_exceptions=True,
        )
    candidates: list[dict] = []
    for res in results:
        if isinstance(res, Exception):
            log.warning("lead candidate source failed: %s", res)
            continue
        candidates.extend(res)
    return candidates


# ---------------------------------------------------------------------------
# Qualify + draft (LLM). Honesty is the whole point: most posts are NOT leads.
# ---------------------------------------------------------------------------
def _products_block(products: dict[str, dict[str, str]]) -> str:
    return "\n".join(
        f'- "{key}" ({p["name"]}): {p["does"]} Genuine fit when: {p["solves"]}'
        for key, p in products.items()
    )


def _candidates_block(candidates: list[dict]) -> str:
    lines = []
    for i, c in enumerate(candidates):
        body = (c.get("body") or "").replace("\n", " ").strip()
        lines.append(
            f'[{i}] ({c["source"]}) {c.get("title", "")}\n'
            f"    says: {body[:500]}"
        )
    return "\n".join(lines)


def _classify(client: anthropic.Anthropic, candidates: list[dict],
              products: dict[str, dict[str, str]]) -> list[dict]:
    """One batched call. Returns [{index, product, fit_score, rationale}] for the
    candidates that GENUINELY fit a product. Strict by design — a marketer would
    tag everything; a good analyst tags almost nothing."""
    if not candidates:
        return []
    prompt = f"""You screen public posts to find people RadarWindow's owner could genuinely help.

PRODUCTS:
{_products_block(products)}

POSTS:
{_candidates_block(candidates)}

For each post, decide: is this person voicing a problem one of these products GENUINELY solves — such that a helpful reply mentioning it would be welcome, not spam?

Be strict. Most posts are NOT a fit. Reject: articles/news, people already using a competitor and happy, vague interest, posts where mentioning a product would feel like an ad. A fit means a real person with the specific pain, asking or clearly stuck.

Return ONLY a JSON array (no preamble, no fences) of the FITS only:
[{{"index": 0, "product": "costwindow", "fit_score": 0.0-1.0, "rationale": "one line, honest — why this is a real fit"}}]
Omit every post that is not a genuine fit. Empty array [] if none fit."""

    r = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = r.content[0].text.strip()
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        log.warning("lead classify: no JSON array in response")
        return []
    try:
        rows = json.loads(re.sub(r",(\s*[}\]])", r"\1", text[start:end + 1]))
    except json.JSONDecodeError as exc:
        log.warning("lead classify: parse failed (%s)", exc)
        return []
    out = []
    for row in rows:
        try:
            idx = int(row["index"])
            product = str(row["product"]).lower().strip()
            if product not in products or not (0 <= idx < len(candidates)):
                continue
            out.append({
                "index": idx,
                "product": product,
                "fit_score": max(0.0, min(float(row.get("fit_score", 0)), 1.0)),
                "rationale": str(row.get("rationale", "")).strip(),
            })
        except (KeyError, ValueError, TypeError):
            continue
    return out


def _draft(client: anthropic.Anthropic, candidate: dict, product_key: str) -> str:
    """Draft a helpful-FIRST reply. Answer the person's real problem so the reply
    stands on its own even if they never touch the product; mention the product
    once, low-key, only if it honestly fits; never a pitch, never a link."""
    p = PRODUCTS[product_key]
    platform = candidate["source"]
    prompt = f"""You are the owner, an independent builder who made {p['name']}. You are replying to a real person on {platform}, as a helpful peer — not marketing.

THEIR POST:
Title: {candidate.get('title', '')}
Body: {candidate.get('body', '')}

{p['name']} is {p['does']}
If (and only if) it genuinely fits their problem, you may mention it once, like this in spirit: "{p['pitch']}"

WRITE A REPLY THAT:
- FIRST actually helps with their specific problem — real, concrete advice they can use even if they never hear of the product. This is most of the reply.
- Mentions {p['name']} at most once, low-key, only if it honestly fits. If the honest answer doesn't need it, don't mention it at all.
- Does NOT include a link (links read as spam and get filtered). Name it; let them look it up.
- Sounds like a person: plain, specific, humble. No marketing adjectives, no "game-changing", "unlock", "leverage". No hype. On Reddit/HN: no emoji, no sign-off, no "Great question".
- Is short — a few sentences. Match how a helpful human actually replies.

Return ONLY the reply text. No preamble, no quotes around it."""

    r = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return r.content[0].text.strip()


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
async def find_leads(cfg: dict, skip_urls: set[str] | None = None) -> list[Lead]:
    """Find + qualify + draft. Returns queued Lead objects (status=pending).
    `skip_urls` are already-seen thread URLs to avoid re-drafting."""
    skip = skip_urls or set()
    products = _focus_products()

    raw = await _gather_candidates(cfg)
    # Dedupe by URL and drop anything already queued.
    candidates: list[dict] = []
    seen: set[str] = set()
    for c in raw:
        url = c.get("url", "")
        if not url or url in seen or url in skip:
            continue
        seen.add(url)
        candidates.append(c)
    candidates = candidates[: settings.LEADS_CANDIDATE_CAP]
    log.info("lead-finder: %d fresh candidates after dedupe", len(candidates))
    if not candidates:
        return []

    client = _llm_client()
    fits = _classify(client, candidates, products)
    fits = [f for f in fits if f["fit_score"] >= settings.LEADS_FIT_THRESHOLD]
    fits.sort(key=lambda f: f["fit_score"], reverse=True)
    fits = fits[: settings.LEADS_MAX_DRAFTS]
    log.info("lead-finder: %d candidates cleared the fit threshold", len(fits))

    leads: list[Lead] = []
    for f in fits:
        c = candidates[f["index"]]
        try:
            reply = _draft(client, c, f["product"])
        except Exception as exc:
            log.warning("lead draft failed for %s: %s", c.get("url"), exc)
            continue
        leads.append(Lead(
            source=SourceName(c["source"]),
            product=f["product"],
            url=c["url"],
            title=c.get("title", "") or c["url"],
            excerpt=(c.get("body") or "")[:500],
            author=c.get("author"),
            fit_score=f["fit_score"],
            rationale=f["rationale"],
            draft_reply=reply,
            created_at=datetime.now(timezone.utc),
        ))
    return leads


def render_leads_email(leads: list[Lead]) -> str:
    """Email body: each lead as a card with the thread link, why it fits, the
    person's words, and the drafted reply in a copy-paste box. The owner posts these
    by hand — the header says so plainly."""
    if not leads:
        return "<p>No new leads cleared the bar this run.</p>"

    cards = []
    for ld in leads:
        pname = PRODUCTS.get(ld.product, {}).get("name", ld.product)
        cards.append(
            "<div style='border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin-bottom:16px'>"
            f"<div style='font-size:12px;color:#6b7280'>{ld.source.value} · "
            f"<strong style='color:#0f766e'>{_html.escape(pname)}</strong> · "
            f"fit {ld.fit_score:.0%}</div>"
            f"<div style='font-weight:600;margin:6px 0'>"
            f"<a href='{_html.escape(ld.url, quote=True)}' style='color:#111827'>"
            f"{_html.escape(ld.title)}</a></div>"
            f"<div style='font-size:13px;color:#374151;margin-bottom:8px'>"
            f"<em>Why it fits:</em> {_html.escape(ld.rationale)}</div>"
            f"<div style='font-size:13px;color:#6b7280;border-left:3px solid #e5e7eb;"
            f"padding-left:10px;margin-bottom:10px'>{_html.escape(ld.excerpt)}</div>"
            "<div style='font-size:12px;color:#6b7280;margin-bottom:4px'>Draft reply "
            "(edit it, make it yours, then post it):</div>"
            "<div style='background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;"
            f"padding:12px;font-size:14px;white-space:pre-wrap'>{_html.escape(ld.draft_reply)}</div>"
            f"<div style='margin-top:8px'><a href='{_html.escape(ld.url, quote=True)}' "
            f"style='font-size:13px;color:#0f766e;font-weight:600'>Open the thread &rarr;</a></div>"
            "</div>"
        )
    return (
        f"<p>Found <strong>{len(leads)}</strong> "
        f"{'person' if len(leads) == 1 else 'people'} you could genuinely help. "
        "Each has a draft reply — <strong>you post them yourself</strong>, in your own "
        "words. RadarWindow never sends these.</p>"
        "<p style='font-size:13px;color:#6b7280'>Answer their problem first; the product "
        "mention is optional. If a draft feels like an ad, bin it.</p>"
        + "".join(cards)
    )
