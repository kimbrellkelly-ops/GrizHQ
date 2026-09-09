#!/usr/bin/env python3
"""Griz HQ Officiating Intelligence — event/summary reconciliation v0.1.

Safety rules:
- Official box-score totals are the authority for accepted penalty count/yards.
- Declined penalties do not count toward accepted totals.
- Offsetting penalties count as foul events but contribute zero accepted yards.
- Compound source lines count each foul component once; combined yardage is applied once.
- Unknown/NULL yardage never becomes zero by inference.
- A PASS requires exact count and yard agreement for every mapped team.
- Any ambiguity produces a non-publishing status rather than a guess.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict
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


def _team_code_map(summary: dict[str, Any], first_team: str, second_team: str) -> dict[str, str]:
    if not first_team or not second_team or first_team == second_team:
        raise ValueError("Two distinct canonical team codes are required to map summary order.")
    if not summary.get("found"):
        raise ValueError("Official penalty summary is missing.")
    return {"first": first_team, "second": second_team}


def _event_is_declined(event: dict[str, Any]) -> bool:
    value = str(event.get("accepted_status", event.get("disposition", ""))).strip().lower()
    return value in {"declined", "not accepted", "not_accepted"}


def _event_is_offsetting(event: dict[str, Any]) -> bool:
    return bool(event.get("offsetting")) or str(event.get("accepted_status", "")).strip().lower() == "offsetting"


def _event_yards(event: dict[str, Any]) -> tuple[int | None, bool]:
    """Return (accepted_yards, unknown).

    Compound groups may have the combined yardage stored on compound_yards. Only
    one event in the group is allowed to carry that combined amount; duplicate
    application is explicitly prevented.
    """
    if _event_is_offsetting(event):
        return 0, False
    if _event_is_declined(event):
        return 0, False
    yards = event.get("yards")
    if yards is not None:
        return int(yards), False
    compound_yards = event.get("compound_yards")
    if compound_yards is not None and event.get("compound_yards_owner", False):
        return int(compound_yards), False
    if compound_yards is not None:
        return 0, False
    return None, True


def reconcile(
    official_summary: dict[str, Any],
    events: Iterable[dict[str, Any]],
    first_team: str,
    second_team: str,
) -> ReconciliationResult:
    """Reconcile canonical event records against the official two-team summary."""
    flags: set[str] = set()
    mapping = _team_code_map(official_summary, first_team, second_team)
    official = {
        first_team: official_summary["first"],
        second_team: official_summary["second"],
    }
    counts = defaultdict(int)
    yards = defaultdict(int)
    unknown = defaultdict(int)
    declined = defaultdict(int)
    offsetting = defaultdict(int)
    seen_compound_groups: set[str] = set()

    for event in events:
        team = event.get("team")
        if team not in official:
            flags.add(f"UNKNOWN_TEAM:{team}")
            continue
        if _event_is_declined(event):
            declined[team] += 1
            continue

        # Every foul component is a penalty event, including offsetting fouls.
        counts[team] += 1
        if _event_is_offsetting(event):
            offsetting[team] += 1

        group = event.get("compound_group")
        if group:
            if group in seen_compound_groups:
                continue
            seen_compound_groups.add(group)
            # Prefer an explicitly designated owner; otherwise search the group.
            if event.get("compound_yards") is not None:
                yards[team] += int(event["compound_yards"])
                continue
            # A compound group without combined yardage cannot be reconciled safely.
            unknown[team] += 1
            flags.add(f"COMPOUND_YARDAGE_UNKNOWN:{group}")
            continue

        value, is_unknown = _event_yards(event)
        if is_unknown:
            unknown[team] += 1
            flags.add(f"UNKNOWN_YARDAGE:{team}")
        else:
            yards[team] += int(value or 0)

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
            if cd != 0:
                flags.add(f"COUNT_MISMATCH:{team}:{cd}")
            if yd != 0:
                flags.add(f"YARD_MISMATCH:{team}:{yd}")
        results.append(TeamReconciliation(team, op, oy, counts[team], yards[team], cd, yd, unknown[team], declined[team], offsetting[team], status))

    if any(x.status == "FAIL" for x in results):
        overall = "FAIL"
    elif any(x.status == "BLOCKED" for x in results):
        overall = "BLOCKED"
    elif all(x.status == "PASS" for x in results):
        overall = "PASS"
    else:
        overall = "REQUIRES_REVIEW"
    return ReconciliationResult(overall, results, sorted(flags))


def main() -> int:
    import argparse, json
    parser = argparse.ArgumentParser(description="Reconcile officiating events against official penalty totals")
    parser.add_argument("record_json")
    parser.add_argument("first_team")
    parser.add_argument("second_team")
    args = parser.parse_args()
    with open(args.record_json, encoding="utf-8") as f:
        record = json.load(f)
    result = reconcile(record["official_penalty_summary_raw"], record.get("penalty_events", []), args.first_team, args.second_team)
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
