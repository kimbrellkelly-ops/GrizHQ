# Real-game validation findings — 2026-09-09

## Southern Utah 2026
GoGriz reports SUU 9-94 and UM 3-32. The PBP contains an offsetting SUU/UM unsportsmanlike sequence. Offsetting fouls are foul events but are excluded from accepted team penalty totals by reconciliation.

## Drake 2026
Current GoGriz reports DU 6-30 and UM 16-138. The PBP contains four Drake false starts (5 each), one Drake delay of game (5), and an intentional grounding event with no explicit yardage. The visible false-start plus delay yardage is 25; the remaining 5 yards in the official total are not assigned to the grounding event because the PBP does not state the yardage. This remains **EVENT_LEVEL_YARDAGE_REVIEW**.

## Idaho 2025
GoGriz reports UI 3-30 and UM 7-72. The PBP contains a compound Montana pass-interference + unsportsmanlike line with combined 30 yards. The event structure is suitable for the compound-yardage reconciliation path.

## Central Washington 2025
GoGriz reports CWU 3-25 and UM 8-85. The PBP includes a declined Montana holding, multiple explicit accepted fouls, and a compound UM holding + personal-foul line. An intentional-grounding event has no explicit yardage; that missing event detail remains separate from the official team total.

## Idaho State 2025
GoGriz reports ISU 3-25 and UoM 4-52. The PBP uses `UoM` as Montana's team token. The parser now normalizes that alias to `UM` while preserving the original source text. Visible accepted Montana events currently account for 37 yards plus an offsetting foul; one 15-yard source event remains unresolved.

## Rule
Never force a PASS by allocating missing yardage from the official total. Source discrepancies and incomplete event-level records remain visible and non-publishable until independently resolved.
