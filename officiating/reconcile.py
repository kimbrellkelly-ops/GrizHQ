#!/usr/bin/env python3
"""Griz HQ Officiating Intelligence — event/summary reconciliation v0.2."""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass
class TeamReconciliation:
    team: str
    official_penalties: int | None
    official_yards: int | None
    parsed_accepted_penalties: int
    parsed_accepted_yards: int
    count_delta: int | None
    yards_delta: int | None
    unknown_yard_events: int
    declined_events: int
    offsetting_events: int
    status: str


@dataclass
class ReconciliationResult:
    status: str
    teams: list[TeamReconciliation]
    flags: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status, "teams": [asdict(x) for x in self.teams], "flags": self.flags}


def _event_raw(event: dict[str, Any]) -> str:
    return str(event.get("raw_text", ""))


def _declined(event: dict[str, Any]) -> bool:
    value = str(event.get("accepted_status", event.get("disposition", ""))).strip().lower()
    return value in {"declined", "not accepted", "not_accepted"} or bool(re.search(r"\bdeclined\b", _event_raw(event), re.I))


def _offsetting(event: dict[str, Any]) -> bool:
    value = str(event.get("accepted_status", "")).strip().lower()
    return bool(event.get("offsetting")) or value == "offsetting" or bool(re.search(r"\boffsetting\b", _event_raw(event), re.I))


def reconcile(official_summary: dict[str, Any], events: Iterable[dict[str, Any]], first_team: str, second_team: str) -> ReconciliationResult:
    """Compare normalized events with the official two-team summary.

    The official summary represents accepted team penalties. Offsetting fouls
    remain visible as events and are counted separately, but are excluded from
    accepted-penalty count and accepted-yard totals. Source-order team mapping
    is explicit; the engine never guesses it.
    """
    flags: set[str] = set()
    if not official_summary.get("found"):
        return ReconciliationResult("BLOCKED", [], ["NO_OFFICIAL_SUMMARY_FOUND"])
    if not first_team or not second_team or first_team == second_team:
        return ReconciliationResult("BLOCKED", [], ["INVALID_TEAM_MAPPING"])

    official = {first_team: official_summary["first"], second_team: official_summary["second"]}
    counts = defaultdict(int)
    yards = defaultdict(int)
    unknown = defaultdict(int)
    declined = defaultdict(int)
    offsetting = defaultdict(int)
    seen_compound: set[str] = set()

    for event in events:
        team = str(event.get("team", ""))
        if team not in official:
            flags.add(f"UNKNOWN_TEAM:{team}")
            continue
        if _declined(event):
            declined[team] += 1
            continue
        if _offsetting(event):
            offsetting[team] += 1
            continue

        counts[team] += 1
        group = event.get("compound_group")
        if group:
            group = str(group)
            if group in seen_compound:
                continue
            seen_compound.add(group)
            combined = event.get("compound_yards")
            if combined is None:
                unknown[team] += 1
                flags.add(f"COMPOUND_YARDAGE_UNKNOWN:{group}")
            else:
                yards[team] += int(combined)
            continue

        value = event.get("yards")
        if value is None:
            unknown[team] += 1
            flags.add(f"UNKNOWN_YARDAGE:{team}")
        else:
            yards[team] += int(value)

    results: list[TeamReconciliation] = []
    for team in (first_team, second_team):
        op = official[team].get("penalties")
        oy = official[team].get("yards")
        cd = counts[team] - op if op is not None else None
        yd = yards[team] - oy if oy is not None else None
        status = "PASS"
        if op is None or oy is None:
            status = "BLOCKED"
            flags.add(f"MISSING_OFFICIAL_TOTALS:{team}")
        elif unknown[team]:
            status = "BLOCKED"
        elif cd != 0 or yd != 0:
            status = "FAIL"
            if cd:
                flags.add(f"COUNT_MISMATCH:{team}:{cd}")
            if yd:
                flags.add(f"YARD_MISMATCH:{team}:{yd}")
        results.append(TeamReconciliation(team, op, oy, counts[team], yards[team], cd, yd, unknown[team], declined[team], offsetting[team], status))

    if any(x.status == "FAIL" for x in results):
        status = "FAIL"
    elif any(x.status == "BLOCKED" for x in results):
        status = "BLOCKED"
    else:
        status = "PASS"
    return ReconciliationResult(status, results, sorted(flags))
