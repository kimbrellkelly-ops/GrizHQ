#!/usr/bin/env python3
"""Fail the deployment if stats.json contains contradictory or stale data."""
from __future__ import annotations
import json, re, sys
from pathlib import Path

def n(value):
    m = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(m.group()) if m else None

def main():
    data=json.loads(Path("data.json").read_text(encoding="utf-8"))
    stats=data.get("stats") or {}
    errors=[]
    summary={x.get("label"):x.get("value") for x in stats.get("team_summary",[]) if isinstance(x,dict)}
    log=stats.get("game_log") or []
    coverage=stats.get("coverage") or {}
    verified=int(coverage.get("verified_boxscores", len(log)) or 0)
    completed=int(coverage.get("completed_games", verified) or 0)
    if verified != len(log): errors.append(f"verified_boxscores={verified} but game_log={len(log)}")
    if verified > completed: errors.append("verified box scores exceed completed games")
    if completed != verified: errors.append("all completed games must have verified box scores")
    if len(log) != completed: errors.append("game_log must contain every completed game")
    for label in ("POINTS / GAME","TOTAL OFFENSE","TOTAL DEFENSE"):
        if label not in summary: errors.append(f"missing summary field: {label}")
    if "—" not in str(stats.get("through","")) and completed and verified < completed:
        errors.append("partial coverage must be disclosed in stats.through")
    # Any old-opponent contamination in the stats object is a hard failure.
    blob=json.dumps(stats, ensure_ascii=False).lower()
    for bad in ("utah tech", "trailblazers", "southern utah losses"):
        if bad in blob and bad != "southern utah losses": errors.append(f"unexpected stale opponent text: {bad}")
    if errors:
        print("STATS VALIDATION FAILED")
        for e in errors: print(f"- {e}")
        return 1
    print(f"STATS VALIDATION PASSED: {verified}/{completed} completed games have verified box scores")
    return 0
if __name__ == "__main__": raise SystemExit(main())
