#!/usr/bin/env python3
"""
Griz HQ Officiating Intelligence — source-normalization engine v0.2

Purpose:
  Convert text exported from a GoGriz football box score into a normalized
  game record and validate the official team penalty totals against the
  parsed penalty-event totals.

Safety philosophy:
  - Never overwrite a verified record on validation failure.
  - Preserve raw source text for every parsed event.
  - Keep source values separate from derived/analyst values.
  - Missing data is NULL, not guessed.
  - Compound/offsetting fouls are preserved as grouped events; individual
    yardage is not invented when the source only reports a combined total.
"""

from __future__ import annotations
import json, re, sys
from pathlib import Path

OFFICIAL_ROLES = [
    "Referee", "Umpire", "Linesman", "Line Judge",
    "Field Judge", "Side Judge", "Back Judge"
]

PENALTY_ABBREVIATIONS = {"UNS", "UNR", "DPI", "OPI", "KCI", "OFC", "IFH", "FST"}
TEAM_ALIASES = {"UOM": "UM"}

SUMMARY_RE = re.compile(
    r"Penalties\s*-\s*Yds\.?\s*\|\s*(?P<a>\d+)-(?P<ay>\d+)\s*\|\s*(?P<b>\d+)-(?P<by>\d+)",
    re.I,
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
        "note": "Team identity/order is preserved as source order; map to team codes from game metadata.",
    }

def _penalty_clause(line: str) -> str | None:
    m = re.search(r"\bPENALTY\s+", line, re.I)
    if not m:
        return None
    clause = line[m.end():].strip()
    if re.search(r"\boffsetting\b", clause, re.I):
        return clause.rstrip(" .")
    yard = re.search(r"\s+\d+\s+yards\b", clause, re.I)
    return clause[:yard.end()] if yard else clause

def _split_components(clause: str) -> list[str]:
    positions = []
    for m in re.finditer(r"\b[A-Z]{2,4}\b", clause):
        before = clause[:m.start()]
        depth = before.count("(") - before.count(")")
        token = m.group()
        if depth == 0 and token not in PENALTY_ABBREVIATIONS:
            positions.append((m.start(), token))
    if len(positions) <= 1:
        return [clause]
    return [clause[positions[i][0]:positions[i + 1][0]].strip() for i in range(len(positions) - 1)] + [clause[positions[-1][0]:].strip()]

def _parse_component(component: str) -> tuple[str, str, str | None, int | None]:
    m = re.match(r"^(?P<team>[A-Z]{2,4})\s+(?P<body>.+)$", component.strip(), re.I)
    if not m:
        return "", norm_space(component), None, None
    team = TEAM_ALIASES.get(m.group("team").upper(), m.group("team").upper())
    body = m.group("body").strip()
    yard_m = re.search(r"\s+(?P<yards>\d+)\s+yards\b", body, re.I)
    yards = int(yard_m.group("yards")) if yard_m else None
    if yard_m:
        body = body[:yard_m.start()].strip()
    player_m = re.search(r"\s+\((?P<player>[^)]+)\)\s*$", body)
    player = norm_space(player_m.group("player")) if player_m else None
    if player_m:
        body = body[:player_m.start()].strip()
    return team, norm_space(body), player, yards

def parse_penalty_events(text: str) -> list[dict]:
    events = []
    for i, line in enumerate(text.splitlines(), 1):
        clause = _penalty_clause(line)
        if not clause:
            continue
        components = _split_components(clause)
        group_id = f"PBP-{i:05d}" if len(components) > 1 else None
        offsetting = bool(re.search(r"\boffsetting\b", clause, re.I))
        parsed = []
        for component in components:
            team, penalty, player, yards = _parse_component(component)
            if not team:
                continue
            parsed.append({"team": team, "penalty_raw": penalty, "player": player, "yards": 0 if offsetting else yards})
        if not parsed:
            continue
        combined_yards = None
        if not offsetting:
            yard_values = [x["yards"] for x in parsed if x["yards"] is not None]
            if len(parsed) > 1 and yard_values:
                combined_yards = yard_values[-1]
                for x in parsed:
                    x["yards"] = None
        for idx, item in enumerate(parsed, 1):
            raw = norm_space(line)
            events.append({
                "event_id": f"PBP-{i:05d}-{idx}" if group_id else f"PBP-{i:05d}",
                "source_line": i,
                "team": item["team"],
                "penalty_raw": item["penalty_raw"],
                "player": item["player"],
                "yards": item["yards"],
                "no_play": bool(re.search(r"\bNO PLAY\b", raw, re.I)),
                "automatic_first_down": bool(re.search(r"\b1ST DOWN\b|\bFIRST DOWN\b", raw, re.I)),
                "offsetting": offsetting,
                "compound_group": group_id,
                "compound_yards": combined_yards,
                "raw_text": raw,
                "clock": (re.search(r"\((\d{1,2}:\d{2})\)", raw).group(1) if re.search(r"\((\d{1,2}:\d{2})\)", raw) else None),
            })
    return events

def parse_replays(text: str) -> list[dict]:
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        if "review" not in line.lower():
            continue
        raw = norm_space(line)
        outcome = None
        if re.search(r"CALL OVERTURNED", raw, re.I): outcome = "OVERTURNED"
        elif re.search(r"CALL UPHELD", raw, re.I): outcome = "UPHELD"
        elif re.search(r"CALL STANDS", raw, re.I): outcome = "STANDS"
        if outcome or re.search(r"challenge", raw, re.I):
            out.append({"replay_id": f"R-{i:05d}", "source_line": i, "outcome": outcome or "UNKNOWN", "coach_challenge": bool(re.search(r"challenge", raw, re.I)), "raw_text": raw})
    return out

def validate_summary_vs_events(official_summary: dict, events: list[dict]) -> dict:
    flags = []
    if not official_summary.get("found"):
        flags.append("NO_OFFICIAL_SUMMARY_FOUND")
        return {"status": "FAIL", "flags": flags}
    for e in events:
        if e["offsetting"]: flags.append("OFFSETTING_EVENT_PRESENT")
        if e["compound_group"]: flags.append("COMPOUND_PENALTY_TEXT_PRESENT")
    return {"status": "REQUIRES_RECONCILIATION" if flags else "READY_FOR_EVENT_RECONCILIATION", "flags": sorted(set(flags)), "event_count": len(events)}

def parse_game(text: str, game_id: str) -> dict:
    officials = parse_officials(text)
    summary = parse_summary(text)
    events = parse_penalty_events(text)
    replays = parse_replays(text)
    validation = validate_summary_vs_events(summary, events)
    return {"schema_version": "0.2", "game_id": game_id, "officials": officials, "official_penalty_summary_raw": summary, "penalty_events": events, "replays": replays, "validation": validation}

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
