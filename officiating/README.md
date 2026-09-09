# Griz HQ Officiating Intelligence — ingestion engine v0.1

This is a standalone data-layer prototype. It does NOT modify Griz HQ production files.

## Purpose
Parse text exported from a GoGriz football box score into:
- seven-man officials
- official penalty summary
- individual penalty-event candidates
- explicit replay events
- validation flags

## Safety
The engine intentionally does not auto-publish a game. It emits:
- READY_FOR_EVENT_RECONCILIATION
- REQUIRES_RECONCILIATION
- FAIL

A later publisher should only accept a record after its event-level penalties reconcile with the official summary or a documented exception is approved.

## Next milestone
Run the parser against raw page text for Southern Utah 2026, Drake 2026, Idaho 2025, then a fourth game. Improve parsing only when a real source variation requires it.
