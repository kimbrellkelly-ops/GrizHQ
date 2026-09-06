GRIZ HQ PHASE 2 — NEWS AUTOMATION

Upload these files to your GitHub repository:

1. news_update.py
   -> repository ROOT

2. refresh-griz-news.yml
   -> .github/workflows/

What it does:
- Runs automatically every hour.
- Pulls Montana football stories from GoGriz RSS, Google News, and Skyline Sports.
- Filters out Montana State/Bobcats stories.
- Deduplicates stories.
- Keeps older stories as a fallback.
- Updates ONLY news.json.
- Does NOT modify data.json, app.js, index.html, styles.css, or the existing scoreboard workflow.

After uploading:
1. Open GitHub -> Actions.
2. Select "Refresh Griz HQ News".
3. Click "Run workflow" once to test it.
4. Confirm the workflow completes successfully.
5. Check that news.json has updated.

The existing "Refresh Griz HQ data" workflow remains separate.
