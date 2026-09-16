# Griz HQ Scoreboard Rebuild

This is a complete replacement of the scoreboard subsystem.

Architecture:
- GitHub Actions retrieves ESPN college-football scoreboard data server-side.
- The generated `scoreboard/scoreboard-data.json` is committed to the repository.
- The browser reads only that local cache, avoiding browser-to-ESPN loading/CORS problems.
- The FCS section displays the current Stats Perform Top 25 from `data.json`.
- Each ranked team is matched to its ESPN game; teams without a game display BYE.
- The Big Sky section uses ESPN's Big Sky conference feed and includes conference and non-conference games involving Big Sky teams.
- Logos come from the ESPN event/team data.
- The refresh workflow runs every 15 minutes and also runs automatically when this rebuild is uploaded.

Files:
- `refresh_scoreboards.py`
- `scoreboard/scoreboard-config.js`
- `scoreboard/scoreboard-render.js`
- `scoreboard/scoreboard.css`
- `scoreboard/scoreboard-data.json`
- `.github/workflows/refresh-scoreboards.yml`

The existing `index.html` already loads the scoreboard config and renderer, so no page-layout file is included in this rebuild.
