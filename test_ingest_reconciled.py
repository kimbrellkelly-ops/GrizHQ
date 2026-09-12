#!/usr/bin/env python3
"""Regression tests for the GoGriz ingestion -> reconciliation gate."""
from __future__ import annotations

import unittest
from unittest.mock import patch

import ingest_reconciled


class IngestReconciledTests(unittest.TestCase):
    def _record(self):
        return {
            "schema_version": "0.2",
            "game_id": "TEST",
            "official_penalty_summary_raw": {
                "found": True,
                "first": {"penalties": 1, "yards": 10},
                "second": {"penalties": 1, "yards": 0},
            },
            "penalty_events": [
                {"team": "OPP", "yards": 10, "accepted_status": "accepted"},
                {"team": "UM", "yards": 15, "offsetting": True},
            ],
        }

    @patch("ingest_reconciled.ingest_url")
    def test_pass_is_ready(self, ingest):
        ingest.return_value = self._record()
        result = ingest_reconciled.ingest_and_reconcile("https://gogriz.com/test", "TEST", "OPP", "UM")
        self.assertEqual(result["reconciliation"]["status"], "PASS")
        self.assertEqual(result["publication_status"], "READY")

    @patch("ingest_reconciled.ingest_url")
    def test_mismatch_is_blocked(self, ingest):
        record = self._record()
        record["penalty_events"][0]["yards"] = 5
        ingest.return_value = record
        result = ingest_reconciled.ingest_and_reconcile("https://gogriz.com/test", "TEST", "OPP", "UM")
        self.assertEqual(result["reconciliation"]["status"], "FAIL")
        self.assertEqual(result["publication_status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
