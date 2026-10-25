from __future__ import annotations

import logging
import subprocess
import tempfile
import uuid
from pathlib import Path

import anthropic
import httpx

from .config import settings
from .models import Platform, Post, ScoredItem, SignalMood

log = logging.getLogger(__name__)

# Rich-media generation for the kit: a signal-specific image per platform, an
# ambient track matched to signal mood, and a short vertical reel for Instagram.
#
# Designed to DEGRADE GRACEFULLY: every step checks for its key/binary and skips
# (logging why) if absent. With no keys set the pipeline still produces the full
# text kit; the moment FAL_API_KEY is added, imagery AND audio appear in
# the same kit with no other change. Generated files are uploaded to Supabase
# Storage so they get stable public URLs (used by both the kit and Blotato).

_PLATFORM_SIZE = {
    Platform.X: (1024, 1024),
    Platform.LINKEDIN: (1200, 628),
    Platform.INSTAGRAM: (1080, 1350),
}

# Mood → audio character, so the track matches the signal direction.
_MOOD_AUDIO = {
    SignalMood.RISING: "uplifting, building momentum, bright synths, 120 bpm",
    SignalMood.BULLISH: "confident, driving, energetic electronic, 124 bpm",
    SignalMood.CAUTIONARY: "tense, restrained, minimal, 90 bpm",
    SignalMood.NEUTRAL: "calm, focused, ambient, 100 bpm",
}


# ----------------------------------------------------------------------------
# Image — fal.ai
# ----------------------------------------------------------------------------

def _llm_client() -> anthropic.Anthropic:
    """Anthropic client for the image-concept step — proxy-routed (dogfoods
    CostWindow + its hard kill switch) exactly like synthesis when configured."""
    if settings.COSTWINDOW_PROXY_URL:
        return anthropic.Anthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            base_url=settings.COSTWINDOW_PROXY_URL,
            default_headers={"X-CostWindow-Label": settings.COSTWINDOW_PROCESS_LABEL},
        )
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _image_concept(title: str, story: str) -> str:
    """Ask an LLM for ONE concrete, instantly-recognisable visual concept for THIS
    specific story. This is the fix for abstract, disconnected imagery: instead of
    restyling the headline into a radar swirl, the model reads the actual story and
    names a clear subject a reader connects to at a glance. Returns '' on any
    failure so the caller falls back to a title-based concept."""
    try:
        client = _llm_client()
        prompt = (
            "You are the art director for an AI-industry intelligence brief. Given a "
            "headline and its key point, describe ONE concrete, instantly recognisable "
            "visual concept a reader would connect to THIS specific story at a glance.\n\n"
            f"Visual world: {settings.VISUAL_WORLD}.\n\n"
            "Rules:\n"
            "- Depict a CLEAR, identifiable subject — a real object, device, scene or "
            "action. Never an abstract pattern, swirl, or unidentifiable shape.\n"
            "- Make it specific to THIS story, not generic 'AI'. Convey the point through "
            "what the objects ARE and DO — a chip, a torn tag, a needle pegged to its "
            "limit, a thrown switch, a cut cable, a stacked vs toppled pile.\n"
            "- CRITICAL: put NO letters, numbers, words or readouts anywhere in the scene "
            "— no price figures, no gauges or meters showing digits, no labelled buttons, "
            "no text on screens. Image generators render text as garbage. Convey amount and "
            "meaning purely visually: size, quantity, a needle's position, a broken vs whole "
            "object, one big thing next to one small thing.\n"
            "- One or two sentences describing exactly what is in frame.\n\n"
            f"Headline: {title}\n"
            f"Key point: {story[:400]}\n\n"
            "Return only the visual description."
        )
        r = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return r.content[0].text.strip()
    except Exception as exc:
        log.warning("media: image concept LLM failed (%s) — using title fallback", exc)
        return ""


def _image_prompt(top_signal: ScoredItem, story: str = "") -> str:
    """Concrete, story-grounded image prompt in the cohesive AI-centric style."""
    title = top_signal.item.title.split(" — ")[0][:120]
    concept = _image_concept(title, story) or (
        f"a single clear, recognisable object or scene that represents: {title}"
    )
    return (
        f"{concept} "
        f"Style: {settings.VISUAL_AESTHETIC}. Palette: {settings.VISUAL_PALETTE}. "
        "One clear focal subject, uncluttered composition, instantly readable. "
        f"Strictly avoid: {settings.VISUAL_AVOID}. "
        "No text, no words, no numbers, no logos, no watermarks."
    )


def generate_image(prompt: str, size: tuple[int, int]) -> Path | None:
    """Generate one image via fal.ai. Returns local path, or None if no key/failure."""
    if not settings.FAL_API_KEY:
        log.info("media: FAL_API_KEY not set — skipping image generation")
        return None
    w, h = size
    try:
        r = httpx.post(
            f"https://fal.run/{settings.FAL_IMAGE_MODEL}",
            headers={
                "Authorization": f"Key {settings.FAL_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "prompt": prompt,
                "image_size": {"width": w, "height": h},
                "num_images": 1,
                "enable_safety_checker": True,
            },
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        img_url = data["images"][0]["url"]
        img_bytes = httpx.get(img_url, timeout=60).content
        out = Path(tempfile.gettempdir()) / f"rw-img-{uuid.uuid4().hex}.jpg"
        out.write_bytes(img_bytes)
        log.info("media: image generated (%dx%d) → %s", w, h, out.name)
        return out
    except Exception as exc:
        log.warning("media: image generation failed: %s", exc)
        return None


# ----------------------------------------------------------------------------
# Audio — fal.ai Stable Audio (same key as imagery; pennies per track)
# ----------------------------------------------------------------------------

def _audio_url_from_response(data: dict) -> str | None:
    """fal audio models return the file under slightly different keys."""
    for key in ("audio_file", "audio"):
        node = data.get(key)
        if isinstance(node, dict) and node.get("url"):
            return node["url"]
    return None


def generate_audio(mood: SignalMood, duration_s: int = 15) -> Path | None:
    """Generate an instrumental track matched to mood via fal.ai. None if no key/failure."""
    if not settings.FAL_API_KEY:
        log.info("media: FAL_API_KEY not set — skipping audio generation")
        return None
    character = _MOOD_AUDIO.get(mood, _MOOD_AUDIO[SignalMood.NEUTRAL])
    try:
        r = httpx.post(
            f"https://fal.run/{settings.FAL_AUDIO_MODEL}",
            headers={
                "Authorization": f"Key {settings.FAL_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "prompt": f"instrumental, ambient background music for a short video, {character}",
                "seconds_total": duration_s,
            },
            timeout=180,
        )
        r.raise_for_status()
        track_url = _audio_url_from_response(r.json())
        if not track_url:
            log.warning("media: audio response had no file url: %s", str(r.json())[:200])
            return None
        audio_bytes = httpx.get(track_url, timeout=120).content
        suffix = ".mp3" if ".mp3" in track_url else ".wav"
        out = Path(tempfile.gettempdir()) / f"rw-audio-{uuid.uuid4().hex}{suffix}"
        out.write_bytes(audio_bytes)
        log.info("media: audio generated (%s) → %s", mood.value, out.name)
        return out
    except Exception as exc:
        log.warning("media: audio generation failed: %s", exc)
        return None


# ----------------------------------------------------------------------------
# Reel — FFmpeg (free, local)
# ----------------------------------------------------------------------------

def build_reel(image_path: Path, audio_path: Path | None, duration_s: int = 15) -> Path | None:
    """Compose a 9:16 reel from a static image (+ optional audio) via FFmpeg."""
    out = Path(tempfile.gettempdir()) / f"rw-reel-{uuid.uuid4().hex}.mp4"
    # Scale-and-pad the image to 1080x1920 so any aspect ratio fits cleanly.
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x0a0e1a,format=yuv420p"
    )
    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(image_path)]
    if audio_path:
        cmd += ["-i", str(audio_path), "-shortest"]
    cmd += [
        "-t", str(duration_s),
        "-vf", vf,
        "-r", "30",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
    ]
    if audio_path:
        cmd += ["-c:a", "aac", "-b:a", "128k"]
    # Limit ffmpeg threads — past hard machine crashes were FFmpeg saturating CPU.
    cmd += ["-threads", "4", str(out)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=180)
        log.info("media: reel built → %s", out.name)
        return out
    except Exception as exc:
        log.warning("media: reel build failed: %s", exc)
        return None


# ----------------------------------------------------------------------------
# Hosting — Supabase Storage (stable public URLs)
# ----------------------------------------------------------------------------

def upload_to_storage(path: Path, content_type: str) -> str | None:
    """Upload a file to the Supabase Storage bucket and return its public URL."""
    key = f"{uuid.uuid4().hex}/{path.name}"
    url = f"{settings.SUPABASE_URL}/storage/v1/object/{settings.MEDIA_BUCKET}/{key}"
    try:
        r = httpx.post(
            url,
            content=path.read_bytes(),
            headers={
                "Authorization": f"Bearer {settings.SUPABASE_KEY}",
                "apikey": settings.SUPABASE_KEY,
                "Content-Type": content_type,
                "x-upsert": "true",
            },
            timeout=60,
        )
        r.raise_for_status()
        public = f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.MEDIA_BUCKET}/{key}"
        return public
    except Exception as exc:
        log.warning("media: storage upload failed (%s) — leaving local path only", exc)
        return None


# ----------------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------------

def enrich_posts(posts: list[Post], top_signal: ScoredItem, mood: SignalMood) -> None:
    """
    Generate and attach media to posts in place. No-op-safe: with no keys, posts
    keep their text and the kit ships text-only. Image is generated per platform;
    one ambient track + Instagram reel are shared.
    """
    # Ground the image concept in the actual story being posted (the X post is the
    # tightest summary), so the picture matches the words — one concept, reused
    # across platforms at their sizes.
    story = next((p.content for p in posts if p.platform == Platform.X and p.content), "")
    if not story and posts:
        story = posts[0].content or ""
    prompt = _image_prompt(top_signal, story)
    audio = generate_audio(mood)
    audio_public_url: str | None = None  # uploaded once, shared across posts

    for post in posts:
        size = _PLATFORM_SIZE.get(post.platform, (1024, 1024))
        img = generate_image(prompt, size)
        if img:
            post.image_path = str(img)
            public = upload_to_storage(img, "image/jpeg")
            if public:
                post.image_public_url = public

        if post.platform == Platform.INSTAGRAM and post.image_path:
            reel = build_reel(Path(post.image_path), audio)
            if reel:
                post.video_path = str(reel)
                public = upload_to_storage(reel, "video/mp4")
                if public:
                    post.video_public_url = public
        if audio:
            post.audio_path = str(audio)
            if not audio_public_url:
                audio_public_url = upload_to_storage(
                    audio, "audio/wav" if audio.suffix == ".wav" else "audio/mpeg"
                )
            post.audio_public_url = audio_public_url
