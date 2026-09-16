# Griz HQ Scoreboard Cleanup & Rebuild

This replaces the old scoreboard data flow with one source of truth:

ESPN group 81 (FCS) + ESPN group 20 (Big Sky) → GitHub Actions → scoreboard/scoreboard-data.json → browser

The browser does not fetch ESPN. The generic college-football feed is not used for either scoreboard.

Changed existing files:
- index.html — removes the legacy inline scoreboard data controller and loads the isolated scoreboard modules.
- app.js — removes the old main scoreboard renderer/refresh loop.
- live-repair.js — keeps Next Up and scroll behavior; no score rendering.
- rankings-team-logos.js — no longer modifies the scorebar.
- score-scroll.js — scroll-only compatibility helper.
- update_data.py — no longer writes legacy fcs_scores.
- score_refresh.py — deprecated compatibility shim; does not write data.
- .github/workflows/refresh-griz-data.yml — no longer invokes score_refresh.py.

New files:
- scoreboard/scoreboard-config.js
- scoreboard/scoreboard-render.js
- scoreboard/scorebar-render.js
- scoreboard/scoreboard.css
- scoreboard/scoreboard-data.json
- refresh_scoreboards.py
- .github/workflows/refresh-scoreboards.yml

Do not delete styles.css; the new scoreboard CSS is fully scoped and does not depend on the legacy FCS classes.
