# Griz HQ Scoreboard Cleanup

One scoreboard system only:

ESPN group 81 (FCS) + ESPN group 20 (Big Sky) -> GitHub Actions -> `scoreboard/scoreboard-data.json` -> Griz HQ.

The browser does not fetch ESPN scoreboard data directly.

The old inline scoreboard controller, the old FCS renderer in `app.js`, and the old scoreboard write path in `update_data.py` are removed. The data-refresh workflow no longer runs the old score updater. `score_refresh.py` remains only as a compatibility wrapper.

The 2026 Big Sky football field is 13 teams: Montana, Montana State, Idaho, Idaho State, Eastern Washington, Northern Arizona, Northern Colorado, Portland State, Weber State, Southern Utah, Utah Tech, Cal Poly and UC Davis.

Obsolete runtime files no longer loaded by the page: `score-scroll.js`, `live-repair.js`, `scorebar_hotfix.py`.
