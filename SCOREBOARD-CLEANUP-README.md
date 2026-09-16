# Griz HQ Scoreboard Cleanup

The scoreboard now has one source and one renderer:

ESPN group 81 (FCS) + ESPN group 20 (Big Sky) -> GitHub Actions -> scoreboard/scoreboard-data.json -> scoreboard/scoreboard-render.js

The browser does not query ESPN for scoreboard games.

The old inline scoreboard controller and live-repair runtime are removed from index.html. The old FCS scoreboard function/calls are removed from app.js. update_data.py no longer builds the old fcs_scores dataset. score_refresh.py is a compatibility wrapper only.

Active scoreboard workflow: .github/workflows/refresh-scoreboards.yml

Obsolete files that are no longer runtime dependencies and can be deleted from the repository when convenient:
- score-scroll.js
- live-repair.js
- scorebar_hotfix.py

Root-level workflow-looking files are not active GitHub Actions because they are not under .github/workflows; they are left alone to avoid touching unrelated history.
