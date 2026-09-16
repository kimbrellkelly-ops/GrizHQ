# Griz HQ scoreboard rebuild
The browser reads only `scoreboard/scoreboard-data.json`.
GitHub Actions fetches ESPN server-side, validates the ranking list, filters the official 13 Big Sky football teams, and commits a fresh cache.
The renderer never treats missing data as a bye.
