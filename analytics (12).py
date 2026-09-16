"""Derived analytics for Griz HQ Officiating Intelligence."""
from __future__ import annotations
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping


def _games(dataset: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    return list(dataset.get("games", []))


def _other(mapping: Mapping[str, Any], team: str = "Montana") -> float:
    for key, value in mapping.items():
        if key != team and value is not None:
            return float(value)
    return 0.0


def _summary(games: Iterable[Mapping[str, Any]]) -> Dict[str, float]:
    games = list(games)
    mp = sum(float(g.get("official_penalties", {}).get("Montana", 0) or 0) for g in games)
    my = sum(float(g.get("official_yards", {}).get("Montana", 0) or 0) for g in games)
    op = sum(_other(g.get("official_penalties", {})) for g in games)
    oy = sum(_other(g.get("official_yards", {})) for g in games)
    n = len(games)
    return {"games": n, "montana_penalties": mp, "montana_yards": my,
            "opponent_penalties": op, "opponent_yards": oy,
            "montana_penalties_per_game": mp / n if n else 0.0,
            "montana_yards_per_game": my / n if n else 0.0,
            "opponent_penalties_per_game": op / n if n else 0.0,
            "opponent_yards_per_game": oy / n if n else 0.0,
            "penalty_differential": mp - op, "yard_differential": my - oy}


def overview(dataset: Mapping[str, Any]) -> Dict[str, Any]:
    rows = []
    for g in _games(dataset):
        mp = float(g.get("official_penalties", {}).get("Montana", 0) or 0)
        my = float(g.get("official_yards", {}).get("Montana", 0) or 0)
        op = _other(g.get("official_penalties", {}))
        oy = _other(g.get("official_yards", {}))
        rows.append({"game_id": g.get("game_id"), "date": g.get("date"),
                     "opponent": g.get("opponent"), "home_away": g.get("home_away"),
                     "conference_game": bool(g.get("conference_game")),
                     "montana_penalties": mp, "montana_yards": my,
                     "opponent_penalties": op, "opponent_yards": oy,
                     "penalty_differential": mp - op, "yard_differential": my - oy,
                     "event_status": g.get("event_status")})
    return {"sample": _summary(_games(dataset)), "games": rows}


def split_summary(dataset: Mapping[str, Any], dimension: str) -> Dict[str, Any]:
    buckets = defaultdict(list)
    for g in _games(dataset):
        key = ("conference" if g.get("conference_game") else "nonconference") if dimension == "conference_game" else str(g.get(dimension) or "UNKNOWN").lower()
        buckets[key].append(g)
    return {k: _summary(v) for k, v in sorted(buckets.items())}


def crew_history(dataset: Mapping[str, Any]) -> List[Dict[str, Any]]:
    groups = {}
    for g in _games(dataset):
        crew = g.get("crew") or {}
        referee = crew.get("Referee")
        if not referee:
            continue
        row = groups.setdefault(referee, {"referee": referee, "games": 0, "game_ids": [], "montana_penalties": 0.0, "montana_yards": 0.0, "opponent_penalties": 0.0, "opponent_yards": 0.0})
        row["games"] += 1
        row["game_ids"].append(g.get("game_id"))
        row["montana_penalties"] += float(g.get("official_penalties", {}).get("Montana", 0) or 0)
        row["montana_yards"] += float(g.get("official_yards", {}).get("Montana", 0) or 0)
        row["opponent_penalties"] += _other(g.get("official_penalties", {}))
        row["opponent_yards"] += _other(g.get("official_yards", {}))
    for row in groups.values():
        n = row["games"]
        row["montana_yards_per_game"] = row["montana_yards"] / n if n else 0.0
        row["opponent_yards_per_game"] = row["opponent_yards"] / n if n else 0.0
        row["yard_differential"] = row["montana_yards"] - row["opponent_yards"]
    return sorted(groups.values(), key=lambda r: (-r["games"], r["referee"]))


def replay_summary(dataset: Mapping[str, Any]) -> Dict[str, Any]:
    total = overturned = upheld = stands = 0
    for g in _games(dataset):
        r = g.get("replay") or {}
        total += int(r.get("events", 0) or 0)
        overturned += int(r.get("overturned", 0) or 0)
        upheld += int(r.get("upheld", 0) or 0)
        stands += int(r.get("stands", 0) or 0)
    return {"games": len(_games(dataset)), "reviews": total, "overturned": overturned,
            "upheld": upheld, "stands": stands,
            "overturned_rate": overturned / total if total else 0.0}


def build_analytics(dataset: Mapping[str, Any]) -> Dict[str, Any]:
    return {"schema_version": "1.0", "overview": overview(dataset),
            "splits": {"home_away": split_summary(dataset, "home_away"),
                        "conference": split_summary(dataset, "conference_game")},
            "crew_history": crew_history(dataset), "replay": replay_summary(dataset)}
