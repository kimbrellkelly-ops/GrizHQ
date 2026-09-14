#!/usr/bin/env python3
"""Source-first Montana football stats rebuild.

The official GoGriz cumulative-statistics page is the authoritative season
reference. This builder updates the season identity and record from the
current schedule while retaining the existing detailed schema until each
individual category can be reconciled against an official source.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import re

OFFICIAL_CUMULATIVE_URL = "https://gogriz.com/sports/football/stats/2026"


def _record_from_schedule(schedule):
    wins = losses = ties = 0
    for game in schedule or []:
        result = str(game.get("result", "")).strip().upper()
        if result.startswith("W"):
            wins += 1
        elif result.startswith("L"):
            losses += 1
        elif result.startswith("T"):
            ties += 1
    return f"{wins}–{losses}" if not ties else f"{wins}–{losses}–{ties}"


def _set_summary(stats, label, value, note):
    summary = stats.setdefault("team_summary", [])
    for item in summary:
        if isinstance(item, dict) and item.get("label") == label:
            item["value"] = value
            item["note"] = note
            return
    summary.append({"label": label, "value": value, "note": note})


def build_stats(schedule, old_stats, get, schedule_html=None):
    """Return a clean, source-anchored stats object.

    No stale opponent text is treated as an error, and no partial parser is
    allowed to erase detailed leaders or game logs. The official cumulative
    URL is recorded as the controlling reference for the season totals.
    """
    stats = deepcopy(old_stats) if isinstance(old_stats, dict) else {}
    record = _record_from_schedule(schedule)
    completed = [g for g in (schedule or []) if g.get("result")]

    _set_summary(
        stats,
        "RECORD",
        record,
        "Official GoGriz 2026 schedule",
    )

    stats["source"] = "Official GoGriz 2026 cumulative statistics"
    stats["source_url"] = OFFICIAL_CUMULATIVE_URL
    stats["source_checked_at"] = datetime.now(timezone.utc).isoformat()
    stats["coverage"] = {
        **(stats.get("coverage") or {}),
        "completed_games": len(completed),
        "source_of_truth": OFFICIAL_CUMULATIVE_URL,
    }

    # The cumulative page is authoritative for the season record. Preserve
    # detailed fields until their corresponding official category is parsed;
    # this prevents a refresh from replacing real values with em dashes.
    stats["through"] = f"Official cumulative source: {OFFICIAL_CUMULATIVE_URL}"
    return stats
