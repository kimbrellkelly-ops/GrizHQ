Griz HQ — FCS Scoreboard Name Display Fix — 2026-09-08

Surgical patch built directly from the current 11 PM MASTER.

CHANGED:
- app.js — FCS Top 25 team-name display only: removed ellipsis/clipping so full team names can display/wrap.
- index.html — cache-bust only, so the browser loads the patched app.js.

NOT CHANGED:
- Roster data/photos/updater logic
- Depth chart
- Coaches
- Rankings
- News/Social
- Transfers
- Workflows
- FCS scoreboard data sources or other systems

Upload these files only. Do NOT run the roster/data refresh workflow for this patch.
