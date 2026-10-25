from __future__ import annotations

from datetime import datetime

from .models import ScoredItem


def render_digest(signals: list[ScoredItem], date: datetime, health: dict[str, int] | None = None) -> str:
    """
    Render the daily signal digest as compact markdown. Pure function —
    radar + scoring output in, markdown out. No LLM call: the digest is the
    raw intelligence layer, near-zero cost by design.
    """
    lines = [f"# Daily signals — {date:%Y-%m-%d}", ""]

    if not signals:
        lines.append("No signals cleared the radar today.")
    for rank, si in enumerate(signals, start=1):
        lines.append(
            f"{rank}. **[{si.item.title}]({si.item.url})** — {si.item.source.value} · "
            f"score {si.combined_score:.2f} · velocity {si.velocity_score:.2f}"
        )

    if health:
        lines += ["", "## Source health", "", "| source | items |", "|---|---|"]
        lines += [f"| {src} | {n} |" for src, n in sorted(health.items(), key=lambda x: -x[1])]

    return "\n".join(lines) + "\n"
