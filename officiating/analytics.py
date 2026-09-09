"""Derived analytics for Griz HQ Officiating Intelligence.

This module consumes normalized, source-verified game summaries. It deliberately
keeps descriptive statistics separate from subjective call assessment and never
turns a penalty differential into a claim about officiating quality or intent.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping


READY_STATUSES = {"PASS", "READY", "MATCHED", "OFFICIAL_PRIMARY"}


def _games(dataset: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    return list(dataset.get("games", []))


def _opp(g: Mapping[str, Any]) -> str:
    return str(g.get("opponent", "Opponent"))


def _opp_value(mapping: Mapping[str, Any], team: str = "Montana") -> float:
    for key, value in mapping.items():
        if key != team and value is not None:
            return float(value)
    return 0.0


def _sum_games(games: Iterable[Mapping[str, Any]]) -> Dict[str, float]:
    games = list(games)
    mt_pen = sum(float(g.get("official_penalties", {}).get("Montana", 0) or 0) for g in games)
    mt_yards = sum(float(g.get("official_yards", {}).get("Montana", 0) or 0) for g in games)
    opp_pen = sum(_opp_value(g.get("official_penalties", {})) for g in games)
    opp_yards = sum(_opp_value(g.get("official_yards", {})) for g in games)
    n = len(games)
    return {
        "games": n,
        "montana_penalties": mt_pen,
        "montana_yards": mt_yards,
        "opponent_penalties": opp_pen,
        "opponent_yards": opp_yards,
        "montana_penalties_per_game": mt_pen / n if n else 0.0,
        "montana_yards_per_game": mt_yards / n if n else 0.0,
        "opponent_penalties_per_game": opp_pen / n if n else 0.0,
        "opponent_yards_per_game": opp_yards / n if n else 0.0,
        "yard_differential": mt_yards - opp_yards,
        "penalty_differential": mt_pen - opp_pen,
    }


def overview(dataset: Mapping[str, Any]) -> Dict[str, Any]:
    games = _games(dataset)
    rows = []
    for g in games:
        mp = float(g.get("official_penalties", {}).get("Montana", 0) or 0)
        my = float(g.get("official_yards", {}).get("Montana", 0) or 0)
        op = _opp_value(g.get("official_penalties", {}))
        oy = _opp_value(g.get("official_yards", {}))
        rows.append({
            "game_id": g.get("game_id"),
            "season": g.get("season"),
            "date": g.get("date"),
            "opponent": _opp(g),
            "home_away": g.get("home_away"),
            "conference_game": bool(g.get("conference_game", False)),
            "montana_penalties": mp,
            "montana_yards": my,
            "opponent_penalties": op,
            "opponent_yards": oy,
            "penalty_differential": mp - op,
            "yard_differential": my - oy,
            "event_status": g.get("event_status"),
        })
    return {"sample": _sum_games(games), "games": rows}


def split_summary(dataset: Mapping[str, Any], dimension: str) -> Dict[str, Any]:
    """Summarize a controlled split such as home_away or conference_game."""
    buckets: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for g in _games(dataset):
        if dimension == "conference_game":
            key = "conference" if g.get("conference_game") else "nonconference"
        else:
            key = str(g.get(dimension) or "UNKNOWN").lower()
        buckets[key].append(g)
    return {key: _sum_games(value) for key, value in sorted(buckets.items())}


def crew_history(dataset: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Aggregate by referee/crew identity without implying causation."""
    groups: Dict[str, Dict[str, Any]] = {}
    for g in _games(dataset):
        crew = g.get("crew") or {}
        referee = crew.get("Referee")
        if not referee:
            continue
        key = str(referee)
        row = groups.setdefault(key, {"referee": key, "games": 0, "game_ids": [], "montana_penalties": 0.0, "montana_yards": 0.0, "opponent_penalties": 0.0, "opponent_yards": 0.0})
        row["games"] += 1
        row["game_ids"].append(g.get("game_id"))
        row["montana_penalties"] += float(g.get("official_penalties", {}).get("Montana", 0) or 0)
        row["montana_yards"] += float(g.get("official_yards", {}).get("Montana", 0) or 0)
        row["opponent_penalties"] += _opp_value(g.get("official_penalties", {}))
        row["opponent_yards"] += _opp_value(g.get("official_yards", {}))
    for row in groups.values():
        n = row["games"]
        row["montana_yards_per_game"] = row["montana_yards"] / n if n else 0.0
        row["opponent_yards_per_game"] = row["opponent_yards"] / n if n else 0.0
        row["yard_differential"] = row["montana_yards"] - row["opponent_yards"]
    return sorted(groups.values(), key=lambda r: (-r["games"], r["referee"]))


def replay_summary(dataset: Mapping[str, Any]) -> Dict[str, Any]:
    total = overturned = upheld = stands = 0
    games_with_reviews = 0
    for g in _games(dataset):
        r = g.get("replay") or {}
        events = int(r.get("events", 0) or 0)
        total += events
        overturned += int(r.get("overturned", 0) or 0)
        upheld += int(r.get("upheld", 0) or 0)
        stands += int(r.get("stands", 0) or 0)
        if events:
            games_with_reviews += 1
    return {
        "games": len(_games(dataset)),
        "games_with_reviews": games_with_reviews,
        "reviews": total,
        "overturned": overturned,
        "upheld": upheld,
        "stands": stands,
        "overturned_rate": overturned / total if total else 0.0,
    }


def publication_summary(dataset: Mapping[str, Any]) -> Dict[str, Any]:
    statuses = [str(g.get("event_status", "UNKNOWN")) for g in _games(dataset)]
    ready = sum(s in READY_STATUSES for s in statuses)
    return {
        "games": len(statuses),
        "ready": ready,
        "blocked_or_review": len(statuses) - ready,
        "all_event_records_publishable": ready == len(statuses),
        "statuses": dict(sorted((s, statuses.count(s)) for s in set(statuses))),
    }


def build_analytics(dataset: Mapping[str, Any]) -> Dict[str, Any]:
    """Return the complete derived analytics artifact for a dataset."""
    return {
        "schema_version": "1.0",
        "overview": overview(dataset),
        "splits": {
            "home_away": split_summary(dataset, "home_away"),
            "conference": split_summary(dataset, "conference_game"),
        },
        "crew_history": crew_history(dataset),
        "replay": replay_summary(dataset),
        "publication": publication_summary(dataset),
    }
