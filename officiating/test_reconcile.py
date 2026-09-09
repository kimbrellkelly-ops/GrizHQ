#!/usr/bin/env python3
"""Focused regression tests for officiating/reconcile.py."""
from __future__ import annotations

import unittest

from reconcile import reconcile


class ReconciliationTests(unittest.TestCase):
    def test_exact_pass(self):
        summary = {"found": True, "first": {"penalties": 2, "yards": 15}, "second": {"penalties": 1, "yards": 10}}
        events = [
            {"team": "UM", "yards": 10, "accepted_status": "accepted"},
            {"team": "UM", "yards": 5, "accepted_status": "accepted"},
            {"team": "OPP", "yards": 10, "accepted_status": "accepted"},
        ]
        result = reconcile(summary, events, "UM", "OPP")
        self.assertEqual(result.status, "PASS")

    def test_declined_is_excluded(self):
        summary = {"found": True, "first": {"penalties": 1, "yards": 10}, "second": {"penalties": 0, "yards": 0}}
        events = [
            {"team": "UM", "yards": 10, "accepted_status": "accepted"},
            {"team": "UM", "yards": 15, "accepted_status": "declined"},
        ]
        result = reconcile(summary, events, "UM", "OPP")
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.teams[0].declined_events, 1)

    def test_offsetting_fouls_count_but_add_zero_yards(self):
        summary = {"found": True, "first": {"penalties": 1, "yards": 0}, "second": {"penalties": 1, "yards": 0}}
        events = [
            {"team": "UM", "yards": 15, "offsetting": True},
            {"team": "OPP", "yards": 15, "offsetting": True},
        ]
        result = reconcile(summary, events, "UM", "OPP")
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.teams[0].offsetting_events, 1)

    def test_compound_yardage_applied_once(self):
        summary = {"found": True, "first": {"penalties": 2, "yards": 30}, "second": {"penalties": 0, "yards": 0}}
        events = [
            {"team": "UM", "yards": None, "compound_group": "PBP-1", "compound_yards": 30},
            {"team": "UM", "yards": None, "compound_group": "PBP-1", "compound_yards": 30},
        ]
        result = reconcile(summary, events, "UM", "OPP")
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.teams[0].parsed_accepted_yards, 30)

    def test_mismatch_fails_closed(self):
        summary = {"found": True, "first": {"penalties": 2, "yards": 20}, "second": {"penalties": 0, "yards": 0}}
        events = [{"team": "UM", "yards": 10, "accepted_status": "accepted"}]
        result = reconcile(summary, events, "UM", "OPP")
        self.assertEqual(result.status, "FAIL")


if __name__ == "__main__":
    unittest.main()
