#!/usr/bin/env python3
"""Run GoGriz ingestion and reconciliation as one fail-closed step."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from gogriz_adapter import ingest_url
from reconcile import reconcile


def ingest_and_reconcile(url: str, game_id: str, first_team: str, second_team: str, snapshot_path: str | None = None) -> dict:
    record = ingest_url(url, game_id, snapshot_path)
    result = reconcile(record["official_penalty_summary_raw"], record.get("penalty_events", []), first_team, second_team)
    record["reconciliation"] = result.to_dict()
    record["publication_status"] = "READY" if result.status == "PASS" else "BLOCKED"
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch, parse, and reconcile a GoGriz football box score")
    parser.add_argument("url")
    parser.add_argument("game_id")
    parser.add_argument("first_team", help="Team code in the source penalty-summary first position")
    parser.add_argument("second_team", help="Team code in the source penalty-summary second position")
    parser.add_argument("output_json")
    parser.add_argument("--snapshot")
    args = parser.parse_args()

    record = ingest_and_reconcile(args.url, args.game_id, args.first_team, args.second_team, args.snapshot)
    Path(args.output_json).write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps(record["reconciliation"], indent=2))
    return 0 if record["publication_status"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
