# Officiating source audit — 2026-09-09

## Drake 2026
Current GoGriz Team Statistics report **6–30** for Drake and **16–138** for Montana. The PBP contains four explicit Drake false starts, one Drake delay of game, and an intentional grounding event without an explicit yardage value in the PBP. The four false starts plus the delay account for 25 visible yards; the remaining 5 yards in the official 30-yard total are not assigned to an event because the PBP does not state the grounding yardage. The game remains **EVENT_LEVEL_YARDAGE_REVIEW** rather than forcing an invented allocation.

## Southern Utah 2026
Current GoGriz reports **9–94 Southern Utah** and **3–32 Montana**. The PBP includes an offsetting SUU/UM unsportsmanlike sequence; offsetting fouls are tracked as foul events but excluded from accepted team penalty totals in reconciliation.

## Idaho State 2025
Current GoGriz reports **3–25 Idaho State** and **4–52 Montana**. Visible accepted Montana PBP events currently account for three accepted fouls totaling 37 yards plus an offsetting foul. The remaining 15-yard source event is unresolved, so the game remains **SOURCE_RECONCILIATION_REQUIRED**.

## Engineering conclusion
The reconciliation gate is doing its job: incomplete event-level yardage and source discrepancies remain non-publishable. No inferred yardage or corrected official total should be written into the canonical event database without independent evidence.
