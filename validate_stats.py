#!/usr/bin/env python3
"""Validate the published Montana football stats object."""
from __future__ import annotations

import json
import re
from pathlib import Path


def main():
    data = json.loads(Path("data.json").read_text(encoding="utf-8"))
    stats = data.get("stats") or {}
    errors = []
    summary = {
        item.get("label"): item.get("value")
        for item in stats.get("team_summary", [])
        if isinstance(item, dict)
    }
    log = stats.get("game_log") or []
    coverage = stats.get("coverage") or {}
    verified = int(coverage.get("verified_boxscores", len(log)) or 0)
    completed = int(coverage.get("completed_games", verified) or 0)
    through = str(stats.get("through", ""))
    pending_disclosed = "pending" in through.lower()

    # Partial box-score coverage is valid when it is explicitly disclosed.
    # The refresh job may know the completed schedule before every individual
    # box score has been verified.
    if verified > len(log):
        errors.append(f"verified_boxscores={verified} but game_log={len(log)}")
    if verified > completed:
        errors.append("verified box scores exceed completed games")
    if completed != verified and not pending_disclosed:
        errors.append("partial coverage must be disclosed in stats.through")
    if len(log) != completed:
        errors.append("game_log must contain every completed game")

    for label in ("RECORD", "POINTS / GAME", "TOTAL OFFENSE", "TOTAL DEFENSE"):
        if label not in summary:
            errors.append(f"missing summary field: {label}")

    # Opponent names are legitimate data. Only flag known legacy labels when
    # they appear as standalone stale record text, not normal opponent names.
    blob = json.dumps(stats, ensure_ascii=False).lower()
    legacy_patterns = (
        r"southern utah\s+losses",
        r"record\s*[:=]\s*0[-–]3",
        r"record\s*[:=]\s*1[-–]2",
    )
    for pattern in legacy_patterns:
        if re.search(pattern, blob):
            errors.append(f"legacy stats text detected: {pattern}")

    if errors:
        print("STATS VALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"STATS VALIDATION PASSED: {verified}/{completed} completed games have verified box scores")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
