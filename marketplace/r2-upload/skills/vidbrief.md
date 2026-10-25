---
name: vidbrief
description: The owner's general-purpose content engine for short-form social video. Use whenever the owner says "/vidbrief", "make video briefs", "create a video series", "write me videos for [topic or URL]", or anything else that implies generating scripts and briefs for short-form video (TikTok, Reels, Shorts, LinkedIn video). Accepts a URL, a topic, or both. Loads a named voice from the voices/ folder so output stays on-brand across dozens or hundreds of videos. Supports one-off briefs, campaign stacks (driving to a URL), topic clusters (exploring one theme), and ongoing library content. Refuses to guess at voice — if the owner names a voice that isn't on disk, the skill stops and asks rather than improvising a persona.
---

# /vidbrief — Content Engine for Short-Form Social Video

This skill turns a URL, a topic, or both into production-ready short-form video briefs. It is opinionated: strong defaults, named overrides, one voice at a time, no generic output.

## The non-negotiable rules

- **Never invent a voice.** If the owner names a voice (e.g. `voice: quesi`) and the file doesn't exist in `voices/`, STOP and tell her. Do not improvise a persona. A voice that doesn't exist on disk is a voice that can drift from one video to the next — that's the opposite of what this skill is for.
- **Never mix voices in one series.** One voice per run. If the owner wants Quesi videos and River videos, that's two runs.
- **Never ignore voice constraints.** Voice files specify what the speaker never says and never does. Those constraints are hard. If the topic requested would require breaking them, flag it before writing.
- **Never produce without the close.** The close — the discovery hook — is the most important line of every script. If a brief goes out with a weak or absent close, the brief isn't done.

## Step 1 — Parse the request

The owner's prompt will contain some combination of:

- **A URL** — the skill should research the page and the broader subject matter (two passes: the page itself, then the subject around it).
- **A topic** — a theme, concept, or specific subject to build videos around. No research of a URL needed; research the subject directly.
- **A voice flag** — `voice: quesi`, `voice: river`, `voice: neutral`, or similar. If omitted, ask before assuming.
- **A series shape** — campaign, cluster, ongoing, or single. If omitted, ask.
- **A count** — how many videos. If omitted, default to 5 for campaign/cluster, 1 for single, 1 for ongoing (with a prompt to come back for the next one).
- **A length** — 30s, 60s, 90s. If omitted, use the voice file's default.
- **A platform** — TikTok, Reels, Shorts, LinkedIn. If omitted, treat output as platform-agnostic and note which platforms each video is best suited for.
- **A CTA override** — if the owner wants the CTA pointed somewhere other than the voice's default.

If anything critical is missing (voice, topic-or-URL, or series shape for a multi-video run), ask for it one question at a time until confident before producing anything.

## Step 2 — Load the voice

Open `voices/<name>.md` from the skill folder. Read it fully. This file is authoritative for:

- Identity and how the speaker addresses the viewer
- Tone descriptors
- Signature language to use and avoid
- What the speaker never does on camera
- Default script shape
- Opening and closing patterns
- Default CTA
- Default length and pacing

If the voice file is missing, stop and tell the owner. Do not improvise.

If the owner has overridden the CTA or length for this run, use her override — but honour everything else in the voice file.

## Step 3 — Decide the series shape

Three shapes are supported. If the owner hasn't named one, ask.

**Campaign stack.** 3-5 videos building toward one URL or destination. Each video stands alone but the series pulls viewers toward the same CTA. Best when there's a specific launch, product, or page to drive traffic to.

**Topic cluster.** N videos exploring one theme — "water signs," "the four elements," "Chiron placements," "grief across traditions." Each video is a facet of the same topic. Viewers who land on one often click through to others. The cluster has an internal logic; the videos don't have to be watched in order but they add up.

**Ongoing library.** One video at a time, contributing to a long-running body of work. Loosely connected. Each stands fully alone. Good for posting cadence — one per week, one per topic that arises. No pre-planned series structure; the library grows.

**Single.** One video, one topic. No series. Occasional use — most of the owner's work is in the other three shapes.

## Step 4 — Research (if applicable)

If a URL was given, run two research passes:

1. **The page itself** — what's actually on `myaicraft.uk/astrologer` (or wherever). What does it say, what does it offer, what's the call-to-action, who's the product for?
2. **The subject around it** — what's the broader topic? What are the angles people search for? What do creators in this space typically do well, do badly, or not do at all?

If no URL was given (topic mode), skip the first pass and go straight to the subject.

The research informs angle selection in Step 5. It does not get quoted in the scripts. Scripts are the voice's, not the research's.

## Step 5 — Choose distinct angles

For a series, every video must be **structurally distinct**, not just topically adjacent. "Chiron in Aries" and "Chiron in Leo" are topically adjacent but structurally the same — that's fine for a cluster. "What Chiron is asking of you" and "The five Chiron placements that struggle most with intimacy" are structurally distinct — that's better.

For a campaign stack, angles should build toward the CTA. For a cluster, angles should explore the theme from different facets. For ongoing, angle selection is per-video.

Before drafting, name the angle for each video in one line and check them against each other. If two angles would produce scripts that feel interchangeable, replace one.

## Step 6 — Produce the briefs

For each video, produce a complete brief containing:

1. **Angle** — one line naming what this video is about, distinct from the others.
2. **Hook** — the first 1-2 seconds. Cold open into the topic. In voice. No self-introduction unless the voice file specifies one.
3. **Script** — the full narration. In voice. Written to the length specified (default from voice file). Leaves breathing room per the voice's pacing. Every constraint in the voice file respected.
4. **Scene outline** — what the viewer sees while the narration runs. Simple, practical. Suitable for Agent Opus, OpusClip, or any AI video agent, or for a human editor. Describe shots or b-roll concepts, not specific copyrighted footage.
5. **Caption** — the post caption, in the same voice. Stands alone from the video but complements it. No hashtag stuffing.
6. **Hashtags** — 5-10, relevant, not generic. Prefer niche over broad.
7. **Thumbnail concept** — one line. What the still frame communicates.
8. **Close / discovery hook** — called out separately because it's the most important line. What drives the viewer to want more from the speaker.
9. **CTA** — the destination. From the voice file unless overridden.

## Step 7 — Self-check before handing over

Before presenting the briefs to the owner, read each one against the voice file with fresh eyes. Ask:

- Does this sound like the named voice? If read aloud, would the owner recognise it?
- Are all "never use" phrases absent?
- Is the close strong — does it make the viewer feel there is more waiting?
- Are the angles distinct from each other, or do two videos blur?
- Does the length match what was asked?

Fix anything that fails this check before handing over. Do not hand over briefs you know are weak.

## Step 8 — Present

Hand over all briefs in one response, clearly structured, numbered. Start with a one-line summary of what was produced (voice, shape, count, theme, CTA). Then the briefs themselves.

End with a short offer: *"I can adjust the voice, swap an angle, or lengthen any script — just say which."* — to invite iteration, not to close the conversation.

## When NOT to use this skill

- Long-form video scripts (10+ minutes). This skill is for short-form only.
- Editing existing video. Use the dedicated editing workflow, not this skill.
- Content that doesn't need a voice — pure utility explainers where brand voice doesn't matter. Overhead of loading a voice file isn't justified.
- Written-only content (blog posts, newsletters). Different shape, different skill.

## Voice files available

- `voices/quesi.md` — faceless orb, oracle-elder, Matrix-Oracle warmth, tropical + Chinese astrology + Sabian symbols, Golden Thread. CTA: @askquesibot on Telegram.
- `voices/river.md` — gender-neutral spiritual guide, many traditions, inclusion over exclusion, offerings not declarations. CTA: @askriverbot on Telegram.

To add a new voice: create `voices/<name>.md` following the structure of the existing voice files. The skill will pick it up automatically.

## One final reminder

Short-form video is brutal about bad voice. A generic script with Quesi's handle on it is worse than no script at all — it teaches the audience that Quesi is generic. Better to produce three scripts that truly sound like her than five that half-sound like her. If you are uncertain whether a script lands the voice, flag it to the owner rather than handing it over as done.
