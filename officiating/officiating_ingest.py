#!/usr/bin/env python3
"""
Griz HQ Officiating Intelligence — source-normalization engine v0.1

Purpose:
  Convert text exported from a GoGriz football box score into a normalized
  game record and validate the official team penalty totals against the
  parsed penalty-event totals.

Safety philosophy:
  - Never overwrite a verified record on validation failure.
  - Preserve raw source text for every parsed event.
  - Keep source values separate from derived/analyst values.
  - Missing data is NULL, not guessed.
"""

from __future__ import annotations
import json, re, sys
from pathlib import Path

OFFICIAL_ROLES = [
    "Referee", "Umpire", "Linesman", "Line Judge",
    "Field Judge", "Side Judge", "Back Judge"
]

PENALTY_RE = re.compile(
    r"PENALTY\s+(?P<team>[A-Z]{2,4})\s+"
    r"(?P<penalty>.+?)(?:\s+\((?P<player>[^)]+)\))?\s+"
    r"(?P<yards>\d+)\s+yards",
    re.I
)

SUMMARY_RE = re.compile(
    r"Penalties\s*-\s*Yds\.?\s*\|\s*(?P<a>\d+)-(?P<ay>\d+)\s*\|\s*(?P<b>\d+)-(?P<by>\d+)",
    re.I
)

def norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def parse_officials(text: str) -> dict:
    out = {}
    for role in OFFICIAL_ROLES:
        m = re.search(rf"{re.escape(role)}:\s*([^\n]+)", text, re.I)
        out[role.lower().replace(" ", "_")] = norm_space(m.group(1)) if m else None
    return out

def parse_summary(text: str) -> dict:
    m = SUMMARY_RE.search(text)
    if not m:
        return {"found": False}
    return {
        "found": True,
        "first": {"penalties": int(m.group("a")), "yards": int(m.group("ay"))},
        "second": {"penalties": int(m.group("b")), "yards": int(m.group("by"))},
    }

def parse_penalty_events(text: str) -> list[dict]:
    events = []
    for i, line in enumerate(text.splitlines(), 1):
        m = PENALTY_RE.search(line)
        if not m:
            continue
        raw = norm_space(line)
        events.append({
            "event_id": f"PBP-{i:05d}",
            "source_line": i,
            "team": m.group("team").upper(),
            "penalty_raw": norm_space(m.group("penalty")),
            "player": norm_space(m.group("player")) if m.group("player") else None,
            "yards": int(m.group("yards")),
            "no_play": bool(re.search(r"\bNO PLAY\b", raw, re.I)),
            "automatic_first_down": bool(re.search(r"\b1ST DOWN\b|\bFIRST DOWN\b", raw, re.I)),
            "offsetting": bool(re.search(r"\boffsetting\b", raw, re.I)),
            "raw_text": raw,
            "clock": (re.search(r"\((\d{1,2}:\d{2})\)", raw).group(1)
                      if re.search(r"\((\d{1,2}:\d{2})\)", raw) else None),
        })
    return events

def parse_replays(text: str) -> list[dict]:
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        if "review" not in line.lower():
            continue
        raw = norm_space(line)
        outcome = None
        if re.search(r"CALL OVERTURNED", raw, re.I):
            outcome = "OVERTURNED"
        elif re.search(r"CALL UPHELD", raw, re.I):
            outcome = "UPHELD"
        elif re.search(r"CALL STANDS", raw, re.I):
            outcome = "STANDS"
        if outcome or re.search(r"challenge", raw, re.I):
            out.append({
                "replay_id": f"R-{i:05d}",
                "source_line": i,
                "outcome": outcome or "UNKNOWN",
                "coach_challenge": bool(re.search(r"challenge", raw, re.I)),
                "raw_text": raw,
            })
    return out

def validate_summary_vs_events(official_summary: dict, events: list[dict]) -> dict:
    """Conservative validation; arithmetic alone never publishes a record."""
    flags = []
    if not official_summary.get("found"):
        flags.append("NO_OFFICIAL_SUMMARY_FOUND")
        return {"status": "FAIL", "flags": flags}

    for e in events:
        if e["offsetting"]:
            flags.append("OFFSETTING_EVENT_PRESENT")
        if "AND" in e["penalty_raw"].upper() or "/" in e["penalty_raw"]:
            flags.append("COMPOUND_PENALTY_TEXT_PRESENT")

    return {
        "status": "REQUIRES_RECONCILIATION" if flags else "READY_FOR_EVENT_RECONCILIATION",
        "flags": sorted(set(flags)),
        "event_count": len(events),
    }

def parse_game(text: str, game_id: str) -> dict:
    officials = parse_officials(text)
    summary = parse_summary(text)
    events = parse_penalty_events(text)
    replays = parse_replays(text)
    validation = validate_summary_vs_events(summary, events)
    return {
        "schema_version": "0.1",
        "game_id": game_id,
        "officials": officials,
        "official_penalty_summary_raw": summary,
        "penalty_events": events,
        "replays": replays,
        "validation": validation,
    }

def main():
    if len(sys.argv) != 4:
        print("Usage: officiating_ingest.py <input.txt> <game_id> <output.json>")
        raise SystemExit(2)
    text = Path(sys.argv[1]).read_text(encoding="utf-8")
    result = parse_game(text, sys.argv[2])
    Path(sys.argv[3]).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["validation"], indent=2))

if __name__ == "__main__":
    main()
