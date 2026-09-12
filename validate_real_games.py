#!/usr/bin/env python3
"""Validate source snapshots against official GoGriz penalty totals.

This runner is deliberately offline: it consumes normalized text snapshots and
never mutates canonical data. A game is publishable only after an exact PASS.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from officiating_ingest import parse_game
from reconcile import reconcile


def validate_game(manifest: dict, snapshot_dir: Path, game: dict) -> dict:
    path = snapshot_dir / f"{game['game_id']}.txt"
    if not path.exists():
        return {"game_id": game["game_id"], "status": "SOURCE_SNAPSHOT_MISSING", "path": str(path)}
    if not game.get("official_penalties") or not game.get("official_yards"):
        return {"game_id": game["game_id"], "status": "PENDING_OFFICIAL_TOTALS"}

    text = path.read_text(encoding="utf-8")
    record = parse_game(text, game["game_id"])
    result = reconcile(
        record["official_penalty_summary_raw"],
        record.get("penalty_events", []),
        game["source_order"][0],
        game["source_order"][1],
    )
    return {
        "game_id": game["game_id"],
        "status": result.status,
        "reconciliation": result.to_dict(),
        "parser_validation": record["validation"],
        "event_count": len(record.get("penalty_events", [])),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("snapshot_dir")
    parser.add_argument("output")
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    snapshot_dir = Path(args.snapshot_dir)
    results = [validate_game(manifest, snapshot_dir, game) for game in manifest["games"]]
    payload = {"schema_version": "0.1", "results": results}
    Path(args.output).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if all(r["status"] == "PASS" for r in results if r["status"] != "PENDING_OFFICIAL_TOTALS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
