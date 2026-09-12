# Griz HQ Live Score Updater

Upload the contents of this package into the root of the `GrizTestHQ` repository.

## Files

- `.github/workflows/update-live-scores.yml` — runs every 10 minutes and can also be run manually.
- `update_data.py` — refreshes Montana data.
- `score_refresh.py` — refreshes the FCS/Big Sky scoreboard data in `data.json`.
- Supporting updater scripts are included for compatibility with the existing project.

## GitHub upload

1. Upload the `.github` folder and the Python files to the repository root.
2. Commit the changes.
3. Open the repository's **Actions** tab.
4. Select **Update Griz HQ live scores**.
5. Click **Run workflow** once to test it.
6. Confirm that `data.json` changes after the workflow completes.

The website must already be coded to read the refreshed scoreboard data from `data.json`.
