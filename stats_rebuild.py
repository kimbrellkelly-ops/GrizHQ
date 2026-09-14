#!/usr/bin/env python3
"""Compatibility shim.

The previous automatic parser was unsafe: it could replace complete stats with
partial values. Until a full source-verified rebuild is implemented, preserve
the existing stats object rather than publishing destructive partial data.
"""

from __future__ import annotations


def build_stats(schedule, old_stats, get, schedule_html=None):
    """Return the existing stats unchanged.

    This deliberately prevents the refresh job from wiping leaders,
    situational statistics, game logs, or other fields that the partial parser
    cannot rebuild accurately.
    """
    return old_stats
