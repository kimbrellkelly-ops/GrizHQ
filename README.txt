GRIZ HQ — NEWSROOM IMAGE UPGRADE

This upgrade adds automatic article images to the Griz HQ Newsroom.

REPLACE THESE 4 FILES IN YOUR GITHUB REPO:
1. index.html
2. styles.css
3. news.json
4. news_update.py

IMPORTANT:
- Do NOT replace app.js.
- Do NOT replace data.json.
- Do NOT change the scoreboard files.
- Keep your existing GitHub Actions workflow for the news updater.

WHAT IT DOES:
- Pulls the featured image from each article when available.
- Checks og:image, Twitter/social image, schema image, RSS media, and article images.
- Uses hero.jpg as a fallback when a source has no usable image.
- Preserves an existing image if a later refresh temporarily cannot retrieve one.
- Adds source labels such as GoGriz, Skyline Sports, Daily Inter Lake, and Utah Tech Athletics.
- Adds an OPPONENT news filter.
- Fixes the Skyline date fallback so an undated story is NOT falsely stamped with today's date.

CURRENT FEED:
The included news.json already has article images for the current Griz stories where source image URLs were available. The Daily Inter Lake story uses the Griz HQ fallback until its source image can be retrieved by the automated updater.

The news system remains separate from data.json, so this change does not alter the scoreboard, rankings, stats, or schedule automation.
