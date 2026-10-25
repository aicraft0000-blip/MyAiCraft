"""In-process job scheduler — runs the pipeline crons inside the web service.

One Railway service runs everything: uvicorn serves the API, and this
scheduler fires the pipeline jobs on their schedules (each in a subprocess,
so a job crash can never take the web process down). Enabled only when
RUN_SCHEDULER=1 — local dev servers never fire jobs by accident.

Schedules (Europe/London, DST-aware):
    digest      daily        07:00
    leads       daily        08:00
    synthesise  Monday       07:00
    publish     Monday       10:00
    qa          Sunday       09:00   (self-alignment check → rw_qa_reports)
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

log = logging.getLogger("radarwindow.scheduler")

LONDON = ZoneInfo("Europe/London")

# Fire a missed slot up to this late (seconds); later than this, skip to next.
CATCH_UP_WINDOW = 6 * 3600

# (job, hour, minute, weekday-or-None) — weekday 0 = Monday, None = daily.
SCHEDULE: list[tuple[str, int, int, int | None]] = [
    ("digest", 7, 0, None),
    ("leads", 8, 0, None),  # daily cost-horror hunt; per-run caps in config bound LLM spend
    ("synthesise", 7, 0, 0),
    ("publish", 10, 0, 0),
    ("qa", 9, 0, 6),  # weekly self-alignment check (Sunday) — lint + drift + auto-fix
]


def next_run(job: str, hour: int, minute: int, weekday: int | None, now: datetime) -> datetime:
    """Next occurrence of the slot strictly after `now` (tz-aware, London)."""
    candidate = now.astimezone(LONDON).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    while candidate <= now or (weekday is not None and candidate.weekday() != weekday):
        candidate += timedelta(days=1)
    return candidate


async def _run_job(job: str) -> None:
    log.info("scheduler: starting job %s", job)
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "radarwindow.main", f"--job={job}",
    )
    rc = await proc.wait()
    log.info("scheduler: job %s finished (exit %d)", job, rc)


async def _job_loop(job: str, hour: int, minute: int, weekday: int | None) -> None:
    """Tick every minute instead of one long sleep.

    Railway pauses idle containers; a paused process's monotonic clock stops,
    so a long asyncio.sleep silently overshoots its slot (this cost us the
    2026-07-06 07:00 run). A short tick re-reads the wall clock each time and
    fires when the target passes — including catching up a missed slot on
    resume, as long as it's less than CATCH_UP_WINDOW late.
    """
    now = datetime.now(LONDON)
    target = next_run(job, hour, minute, weekday, now)
    log.info("scheduler: %s next at %s", job, target.isoformat())
    while True:
        await asyncio.sleep(60)
        now = datetime.now(LONDON)
        if now < target:
            continue
        late = (now - target).total_seconds()
        if late <= CATCH_UP_WINDOW:
            try:
                await _run_job(job)
            except Exception as exc:  # a failed run must never kill the loop
                log.warning("scheduler: job %s failed: %s", job, exc)
        else:
            log.warning("scheduler: %s slot %s missed by %.0f min — skipping", job, target.isoformat(), late / 60)
        target = next_run(job, hour, minute, weekday, now)
        log.info("scheduler: %s next at %s", job, target.isoformat())


def start(loop: asyncio.AbstractEventLoop | None = None) -> list[asyncio.Task] | None:
    if os.environ.get("RUN_SCHEDULER") != "1":
        log.info("scheduler: disabled (set RUN_SCHEDULER=1 to enable)")
        return None
    if not logging.getLogger().handlers:  # make job logs visible under uvicorn/Railway
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
    tasks = [
        asyncio.ensure_future(_job_loop(job, h, m, wd))
        for job, h, m, wd in SCHEDULE
    ]
    log.info("scheduler: started %d job loops", len(tasks))
    return tasks
