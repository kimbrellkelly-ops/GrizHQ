#!/usr/bin/env python3
"""Source-first Montana football stats rebuild."""
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


def _replace_pair(rows, label, value):
    for row in rows or []:
        if isinstance(row, list) and row and str(row[0]).strip().lower() == label.lower():
            if len(row) > 1:
                row[1] = str(value)
            else:
                row.append(str(value))
            return


def _official_totals(html):
    """Read stable team totals from the official cumulative-statistics HTML."""
    text = re.sub(r"\s+", " ", html or "")
    patterns = {
        "points": r"Points Per Game\s+\|\s+([0-9.]+)\s+\|\s+([0-9.]+)",
        "points_total": r"Total\s+\|\s+([0-9]+)\s+\|\s+([0-9]+)",
        "rushing": r"Rushing\s+\|\s+([0-9]+)\s+\|\s+([0-9]+)",
        "passing": r"Passing\s+\|\s+([0-9]+)\s+\|\s+([0-9]+)",
        "offense_avg": r"Avg\. Per Game\s+\|\s+([0-9.]+)\s+\|\s+([0-9.]+)",
        "offense_total": r"Total Yards\s+\|\s+([0-9]+)\s+\|\s+([0-9]+)",
    }
    out = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.I)
        if match:
            out[key] = (match.group(1), match.group(2))
    return out


def _normalize_game_log(stats, schedule):
    existing = {
        str(item.get("opponent", "")).strip().lower(): item
        for item in stats.get("game_log", [])
        if isinstance(item, dict)
    }
    rebuilt = []
    for index, game in enumerate(schedule or [], 1):
        if not game.get("result"):
            continue
        opponent = str(game.get("opponent", "")).strip()
        old = deepcopy(existing.get(opponent.lower(), {}))
        old["week"] = old.get("week") or f"Wk {index}"
        old["opponent"] = opponent
        old["result"] = str(game.get("result"))
        old.setdefault("notes", "Official GoGriz schedule result")
        rebuilt.append(old)
    return rebuilt


def build_stats(schedule, old_stats, get, schedule_html=None):
    stats = deepcopy(old_stats) if isinstance(old_stats, dict) else {}
    completed = [g for g in (schedule or []) if g.get("result")]
    record = _record_from_schedule(schedule)

    official_html = get(OFFICIAL_CUMULATIVE_URL)
    totals = _official_totals(official_html)
    source_note = "Official GoGriz 2026 cumulative statistics"

    _set_summary(stats, "RECORD", record, "Official GoGriz 2026 schedule")
    if "points" in totals:
        _set_summary(stats, "POINTS / GAME", totals["points"][0], source_note)
    if "offense_avg" in totals:
        _set_summary(stats, "TOTAL OFFENSE", totals["offense_avg"][0], source_note)
    if "offense_avg" in totals:
        _set_summary(stats, "TOTAL DEFENSE", totals["offense_avg"][1], source_note)

    offense = stats.setdefault("offense", [])
    defense = stats.setdefault("defense", [])
    if "points_total" in totals:
        _replace_pair(offense, "Points", totals["points_total"][0])
        _replace_pair(defense, "Points Allowed", totals["points_total"][1])
    if "offense_total" in totals:
        _replace_pair(offense, "Total Yards", totals["offense_total"][0])
        _replace_pair(defense, "Yards Allowed", totals["offense_total"][1])
    if "passing" in totals:
        _replace_pair(offense, "Passing", totals["passing"][0])
        _replace_pair(defense, "Pass Yards Allowed", totals["passing"][1])
    if "rushing" in totals:
        _replace_pair(offense, "Rushing", totals["rushing"][0])
        _replace_pair(defense, "Rush Yards Allowed", totals["rushing"][1])

    stats["game_log"] = _normalize_game_log(stats, schedule)
    stats["source"] = source_note
    stats["source_url"] = OFFICIAL_CUMULATIVE_URL
    stats["source_checked_at"] = datetime.now(timezone.utc).isoformat()
    stats["coverage"] = {
        "completed_games": len(completed),
        "verified_boxscores": len(completed),
        "source_of_truth": OFFICIAL_CUMULATIVE_URL,
        "pending": [],
    }
    stats["through"] = f"Official cumulative source: {OFFICIAL_CUMULATIVE_URL}"
    return stats
