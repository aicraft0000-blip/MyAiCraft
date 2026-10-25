---
name: url-to-video-series
description: Turn any URL into a stacked series of 3–5 short-form social video briefs (30–60 seconds each) engineered to drive traffic back to that URL. Use whenever the owner says "turn this link into videos", "make a video series from this URL", "video briefs for [link]", "Agent Opus from this URL", "/videos", or anything that involves generating social video scripts, hooks, or briefs from a web page. The skill reads the URL, researches the page itself and the broader subject matter in two passes, identifies distinct angles so the videos stack into a coherent series rather than repeating each other, and outputs a full social package per video — hook, brief, script, scene outline, caption, hashtags, thumbnail concept, and CTA back to the URL. Default target is Agent Opus (OpusClip), but the output structure ingests cleanly into any AI video agent. Do NOT use for editing existing videos, for creating videos that don't originate from a URL, or for generating long-form content.
---

# /videos — URL → Stacked Video Series

This skill turns a single URL into a coherent stack of short-form video briefs designed to drive traffic back to that URL. It is not a single-video generator. The default output is a series of **4 videos** (flexing to 3 or 5 only when the subject demands), each tackling a distinct angle of the same subject, sharing a unified visual and tonal DNA so they read as a campaign — not as one video and some spares.

The default text-to-video target is **Agent Opus** (OpusClip), which ingests briefs, scripts, outlines, or blog URLs and produces publish-ready videos with voiceover, motion graphics, and captions. The output format below is tailored to what Agent Opus accepts, but the same structure works for any AI video agent. If the owner names a different platform at invocation, adapt accordingly.

## The non-negotiable rules

These rules apply every time this skill runs.

- **Never invent URL content.** If the URL can't be fetched — paywall, auth wall, broken link, 403, redirect loop — STOP and tell the owner. Do not reason from the URL slug, the domain, or what the page "probably" says. A wrong brief is worse than no brief.
- **Never skip the two research passes.** The first pass (the URL itself) grounds voice, audience, and CTA. The second pass (the subject matter) supplies the stacking angles. Skipping either produces generic, interchangeable videos that don't convert.
- **Never reuse the same hook across the series.** If two videos in the stack would start the same way, that's a planning failure — go back to Step 4 and find a genuinely different angle.
- **Never lift copy verbatim from the source URL.** The scripts should carry the source's message in the owner's (or the brand's) voice, not read like the article. Paraphrase. Reframe. Quote only if the quote itself is the hook.
- **Flag any URL that looks wrong.** Phishing-style domains, URLs that ask for credentials, or links pointing to anything that would put the owner's identity or money at risk → raise a Security Flag in the standard format and stop.

## Step 1 — Capture and validate the URL

Confirm exactly one URL is in scope. If the owner has pasted multiple, ask which one drives the series. If the URL is missing a scheme (no `https://`), add it. If it's a shortlink (bit.ly, t.co, lnkd.in, etc.) resolve it first and work from the destination.

Before fetching, sanity-check:

- Does the domain look legitimate? If not, Security Flag and stop.
- Does the URL require a login to read? If yes, ask the owner to either paste the page content directly or pick a public URL.
- Is this a the owner-owned URL (driving traffic to her own business) or a third-party URL (driving traffic elsewhere)? The owner-owned is the default assumption — if it's third-party, confirm she has a reason before proceeding.

## Step 2 — Read the URL

Use `web_fetch` to retrieve the full page content. Read it end-to-end, not just the first paragraph. You're looking for:

- **What this page is.** Blog post, landing page, product page, case study, podcast episode, newsletter issue, event page, etc.
- **The primary message.** What's the one thing a reader should walk away with?
- **The CTA on the page.** What action is the owner trying to get people to take once they arrive? (Buy, sign up, book a call, read more, download.) Every video in the series will funnel to this.
- **The brand voice.** How does this page talk? Formal/casual, technical/plain-English, witty/earnest. Capture three or four voice markers — specific phrases, sentence rhythms, typical vocabulary — so the video scripts sound like they belong to this brand.
- **The audience.** Who is this page written for? If it's not explicit, infer from the vocabulary and the assumed prior knowledge.
- **Any hard facts, stats, or quotes** that could become hooks.

If the page is extremely long (over ~5000 words), focus on the sections most relevant to the subject and note which sections you skipped. If it's extremely short (under ~200 words) and there isn't enough to research, flag that the page may be too thin to support a 3–5 video series and check with the owner before continuing.

## Step 3 — Research pass 1: the page and its context

With the page content in hand, do a short targeted research pass to ground the brand/page in its wider context. This is a calibration pass, not a deep dive. Around 2–4 searches is typically right.

- Search for the brand/author if not already familiar — what do they publish, what's their angle, what audience do they command?
- Search for the specific topic of the page to understand how it fits into current conversations (is this a hot topic, an evergreen one, a contrarian take?).
- Note anything in the wider conversation that contradicts or complicates the page — this often becomes a useful angle in Step 4.

Skip this pass only if the page is self-contained and the subject needs no contextual grounding (e.g. a straightforward product page).

## Step 4 — Identify 4 distinct angles for the series (flex to 3 or 5)

Default target is **4 angles** — enough to give the series algorithmic momentum, not so many that the subject gets over-mined. Drop to 3 if a fourth angle would clearly duplicate one of the first three. Stretch to 5 only if the subject genuinely supports five distinct frames with different supporting material.

This is the step that makes the series work. Short-form video doesn't tolerate repetition — if videos 2, 3, and 4 all rehash video 1 with different B-roll, the algorithm and the audience both tune out.

For each angle, write one sentence that captures:

- **What part of the subject it attacks.** (A claim, a misconception, a counter-intuitive truth, a how-to, a story, a stat, a prediction, a comparison.)
- **Why this angle earns its own video.** What does it do that the others don't?

Aim for genuine diversity of frame. Common angle families that stack well:

- **The surprising fact** — a stat or detail that sounds wrong but isn't.
- **The common misconception** — what most people believe vs. what's actually true.
- **The contrarian take** — the page's argument reframed against the consensus view.
- **The how-to** — a single, specific, actionable step derived from the page.
- **The story** — a concrete case, example, or anecdote that illustrates the message.
- **The consequence** — what happens if you ignore the page's argument.
- **The comparison** — the page's point vs. a familiar alternative.

Reject angles that are really the same angle wearing different clothes. If you're struggling to get to 3, say so and check with the owner whether the subject genuinely supports a series or whether a single strong video would land better.

## Step 5 — Research pass 2: the subject matter

Now go deep on the subject itself — not the page, the subject. For each angle chosen in Step 4, pull in the specific detail that will make that video distinctive:

- Stats, dates, numbers, dollar figures — concrete hooks beat abstract ones.
- Named examples, case studies, quotes from recognisable figures.
- Recent developments that anchor the video in "this month" rather than "sometime".
- Counter-examples that strengthen the framing.

Usually 1–3 targeted searches per angle. Keep notes on the source for each fact — the scripts will paraphrase, but the owner should be able to verify anything punchy before it goes live.

If a planned angle turns out to have no specific material to anchor it, swap it for a different one from Step 4 rather than writing a vague script.

## Step 6 — Build the video packages

Produce one package per angle, using the exact output format in the next section. Before writing any individual package, decide the **series DNA** — the shared identity that makes this a campaign rather than a list:

- **Audience** (inherited from Step 2).
- **Tone** (inherited from the brand voice in Step 2).
- **Brand voice sample** — capture 3–4 specific voice markers from the URL: a characteristic phrase, a sentence rhythm, typical vocabulary, a tell. Every script in the series reads against this sample. This is what stops the videos sounding like generic AI narration.
- **Visual style** (pick one — e.g. "clean motion graphics on solid colour backgrounds", "fast-cut stock B-roll with text overlays", "avatar-led direct-to-camera", "kinetic typography over music"). For Agent Opus, this maps to the Style Match / avatar choice.
- **Aspect ratio** — 9:16, fixed default. Do not change unless the owner has explicitly asked for a different ratio this run.
- **Unified CTA phrase** — one single call-to-action, spoken the same way at the close of every video in the stack. The destination is always the URL the owner gave you; the *phrasing* of the CTA is derived from the brand voice in Step 2 (e.g. "Full breakdown at the link", "Get the playbook — link below", "Read the piece, it changes things"). Same CTA, every video — that's what trains the audience to associate the series with the destination.
- **Hook formula** — all videos open with the same *shape* of hook, not the same hook. Pick one shape for the series: "surprising stat", "direct question", "stat-first", "contrarian claim", "story cold-open". This gives the stack a consistent on-scroll identity. No narrative warm-ups. No "hey everyone".

Then write each video. Keep script length disciplined:

- **30 seconds** ≈ 75–85 narrated words
- **45 seconds** ≈ 110–125 words
- **60 seconds** ≈ 145–160 words

Agent Opus will stretch or compress, but writing to length upfront produces tighter videos.

## Output format — exact template

Write the final deliverable as a single markdown document with this structure. Do not abbreviate or reorder.

```markdown
# Video Series: [Subject] → [destination URL]

**Source URL:** [URL]
**Page type:** [blog post / landing page / etc.]
**Generated:** [date]

## Series DNA

- **Audience:** [inherited from page]
- **Tone:** [inherited from brand voice]
- **Brand voice sample:** [3–4 specific voice markers from the URL — a characteristic phrase, a rhythm, a vocabulary tell]
- **Visual style:** [chosen style]
- **Aspect ratio:** 9:16
- **Unified CTA phrase:** [the exact words, spoken identically in every video in the series]
- **Hook formula:** [the one shape all videos open with — e.g. "surprising stat", "direct question", "contrarian opener"]

## Research summary

One short paragraph on what the page is and what the broader subject looks like. Three or four bullets with the hard facts / stats / quotes that will anchor the series. Source links for each.

---

## Video 1 of N — [Angle title]

**Length:** 30s | 45s | 60s
**Angle family:** [surprising fact / misconception / contrarian / how-to / story / consequence / comparison]
**Why this video earns its slot:** [one sentence]

### Hook (0–3s)
[The exact opening words. This is the single most important line in the whole package — the scroll-stop. Write it to be said aloud in under three seconds.]

### Brief for Agent Opus
[A 2–3 sentence brief describing the video's purpose, audience, and tone. This is what goes into the "prompt" field if using Agent Opus as a brief-driven workflow.]

### Script
[The full narrated script, written to the chosen length. Paragraphed naturally. Paraphrased from the URL's message, not lifted. Ends with a spoken CTA that points at the URL.]

### Scene outline
[3–6 bullets describing the visual pacing — what's on screen during each beat of the script. Useful for Agent Opus's scene-by-scene generation, or as a shot list if filmed.]
- 0–3s: [hook visual]
- 3–10s: [setup]
- 10–25s: [payoff]
- 25–[end]s: [CTA visual]

### Caption
[The social media post caption — 1–3 sentences. Hook-forward. Ends with a link prompt ("link in bio" / the URL itself depending on platform).]

### Hashtags
[5–10 hashtags, mix of broad reach and niche relevance. One line.]

### Thumbnail concept
[One sentence describing the cover frame — what's visible, what text overlay if any.]

### CTA wording
[The exact CTA line, usable on-screen and in caption.]

---

## Video 2 of N — [Angle title]
[... repeat the structure above ...]

---

[... continue for all videos in the series ...]

---

## Publication order recommendation

[One short paragraph: which video goes out first and why, what order the rest follow, how far apart to space them. Usually: lead with the surprising-fact or contrarian angle to hook cold audiences, follow with how-to or story for warmer engagement, close with the consequence angle to drive urgency.]
```

Save the final document to `/mnt/user-data/outputs/` as `video-series-[short-subject-slug].md` and present it to the owner using `present_files`.

## Agent Opus optimisation notes

When the owner takes these packages into Agent Opus, the Brief, Script, and Scene outline fields map directly:

- **Brief field** → the "Brief for Agent Opus" block
- **Script field** → the "Script" block
- **Outline field** → the "Scene outline" block
- **Hook field** (Agent Opus surfaces this explicitly) → the "Hook (0–3s)" block
- **Aspect ratio** → inherited from the Series DNA
- **Voice / avatar** → the owner's choice at runtime (the skill doesn't prescribe this — her cloned voice and avatar are reusable assets)

If the owner is using a different platform (Sora, Veo, Runway, etc.), the Brief and Script fields still work — those platforms just need more prescriptive visual direction, so lean harder on the Scene outline and thumbnail concept sections.

## When NOT to use this skill

- The owner wants to edit or repurpose an existing video (that's an OpusClip task, not this skill).
- There's no URL involved — the brief comes from a doc, an idea, or a conversation. Use Agent Opus directly.
- The owner wants a single one-off video, not a series, and the subject doesn't need multiple angles. Ask her whether she wants a series at all before spinning one up.
- The URL is behind a login, paywall, or any access barrier that the skill can't read. Resolve that first.
- The URL is a competitor's page or otherwise somewhere the owner shouldn't be sending her audience. Flag and stop.

## One final reminder

The whole point of the stacked series is that each video is a different door into the same room. If two videos feel interchangeable, the stack isn't working — go back to Step 4 and rethink. The owner would rather have three genuinely distinct videos than five near-duplicates.
