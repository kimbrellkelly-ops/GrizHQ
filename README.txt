GRIZ HQ SCOREBOARD REPAIR

Changed files:
1. score_refresh.py
2. .github/workflows/refresh-griz-data.yml
3. index.html

What this fixes:
- FCS scores are cached into data.json by GitHub Actions instead of depending on ESPN browser/CORS access.
- Uses both ESPN public scoreboard endpoints as fallbacks.
- Never deletes an existing good score cache when a request fails.
- Refreshes roughly every 10 minutes.
- The index.html cache-buster forces browsers to load the current scoreboard code.

Upload:
- Replace index.html in the repository root.
- Add score_refresh.py to the repository root.
- Replace .github/workflows/refresh-griz-data.yml with the included workflow.
- Do not replace app.js, styles.css, data.json, images, or CNAME.

After uploading:
1. Open GitHub -> Actions.
2. Choose "Refresh Griz HQ data".
3. Click "Run workflow".
4. Wait for the green check.
5. Refresh grizhq.com with Ctrl+F5.

The first successful run should repopulate data.json with fcs_scores, which the existing app.js already reads for both the FCS Top 25 and Big Sky scoreboard.
