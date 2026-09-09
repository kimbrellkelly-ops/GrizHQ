# Officiating Intelligence v2 — Event Layer

This layer adds the first play-level/event-level research surface without changing protected Griz HQ production systems.

## Added
- `penalty_events_v1.json` — source-visible subset of penalty events from verified GoGriz play-by-play.
- `event-lab.html` — filterable event browser.
- `notable_calls.json` — empty evidence registry for future manually reviewed calls.

## Publication rule
Official team penalty totals remain authoritative. Event records are explicitly marked as a subset until game-level reconciliation reaches PASS. Unknown yardage is never inferred.

## Notable calls
The registry deliberately starts empty. A call cannot receive a correctness label merely because fans disagree with it or because replay changed a ruling. Future records require source evidence, a rule reference where applicable, reviewer identity/status, and one of four assessments: CLEARLY_CORRECT, DEBATABLE, LIKELY_INCORRECT, INSUFFICIENT_EVIDENCE.
