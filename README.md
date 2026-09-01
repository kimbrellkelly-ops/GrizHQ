# Griz HQ — Automatic Data Layer

This version adds a free, GitHub-native automatic data layer.

## What updates automatically
- Montana football schedule and results from GoGriz
- Current record and conference record
- Next opponent/date/time
- AFCA FCS Coaches Poll Top 20
- Stats Perform FCS Top 20
- Latest Montana football RSS headlines
- "Last updated" timestamp

## How it works
GitHub Actions runs every 6 hours and writes fresh values into `data.json`. The site's `app.js` reads that file when the page loads.

## Files to upload
Upload/replace:
- `index.html`
- `styles.css`
- `app.js`
- `data.json`
- `update_data.py`
- `.github/workflows/refresh-griz-data.yml`
- `hero.jpg`

Keep your existing `CNAME` and any other files you already use.

## Important
The automation is intentionally conservative: if an upstream page cannot be parsed during a run, the previous good data remains in `data.json` rather than being overwritten with blanks.

## Branding update
The header and footer now use the supplied Griz paw image (`griz-paw.png`).

## Latest changes
- Reduced the header paw size.
- Added a full offense/defense/special-teams depth chart driven from data.json.
- Depth chart includes the latest published two-deep source and source link.

## Resource update
- Removed BLN branding.
- Added eGriz, Griz Fan Pod/Montana Mint, and Grizzly Sports Radio / Varsity Network resources.
