#!/usr/bin/env python3
"""Regression coverage for source-team aliases found in real GoGriz PBP."""
from __future__ import annotations

import unittest

import officiating_ingest


class TeamAliasTests(unittest.TestCase):
    def test_uom_normalizes_to_um(self):
        text = "PENALTY UoM Pass Interference (Lawler,Kenzel) 15 yards (NO PLAY)"
        events = officiating_ingest.parse_penalty_events(text)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["team"], "UM")
        self.assertEqual(events[0]["yards"], 15)
        self.assertEqual(events[0]["raw_text"], text)


if __name__ == "__main__":
    unittest.main()
