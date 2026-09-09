#!/usr/bin/env python3
"""Regression tests for accepted-penalty reconciliation semantics."""
from __future__ import annotations

import unittest

from reconcile import reconcile


class ReconcileV02Tests(unittest.TestCase):
    def test_offsetting_fouls_are_not_accepted_penalties(self):
        summary = {
            "found": True,
            "first": {"penalties": 0, "yards": 0},
            "second": {"penalties": 0, "yards": 0},
        }
        events = [
            {"team": "DU", "yards": 15, "offsetting": True},
            {"team": "UM", "yards": 15, "offsetting": True},
        ]
        result = reconcile(summary, events, "DU", "UM")
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.teams[0].parsed_accepted_penalties, 0)
        self.assertEqual(result.teams[0].parsed_accepted_yards, 0)
        self.assertEqual(result.teams[0].offsetting_events, 1)

    def test_compound_yardage_is_applied_once(self):
        summary = {
            "found": True,
            "first": {"penalties": 2, "yards": 30},
            "second": {"penalties": 0, "yards": 0},
        }
        events = [
            {"team": "UM", "yards": None, "compound_group": "PBP-1", "compound_yards": 30},
            {"team": "UM", "yards": None, "compound_group": "PBP-1", "compound_yards": 30},
        ]
        result = reconcile(summary, events, "UM", "OPP")
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.teams[0].parsed_accepted_yards, 30)


if __name__ == "__main__":
    unittest.main()
