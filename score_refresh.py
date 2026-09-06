import json
from datetime import datetime, timezone
from pathlib import Path
import requests

DATA = Path("data.json")

WEEKS = [
    ("2026-08-27", "2026-08-30"),
    ("2026-09-03", "2026-09-06"),
    ("2026-09-10", "2026-09-13"),
    ("2026-09-17", "2026-09-20"),
    ("2026-09-24", "2026-09-27"),
    ("2026-10-01", "2026-10-04"),
    ("2026-10-08", "2026-10-11"),
    ("2026-10-15", "2026-10-18"),
    ("2026-10-22", "2026-10-25"),
    ("2026-10-29", "2026-11-01"),
    ("2026-11-05", "2026-11-08"),
    ("2026-11-12", "2026-11-15"),
    ("2026-11-19", "2026-11-22"),
]

URLS = [
    "https://site.web.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard",
    "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard",
]

HEADERS = {"User-Agent": "GrizHQ/1.0 (+https://grizhq.com)"}

def fetch_week(start, end):
    params = {
        "dates": f"{start.replace('-', '')}-{end.replace('-', '')}",
        "groups": "81",
        "limit": 500,
    }

    last_error = None

    for url in URLS:
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=30)
            r.raise_for_status()
            payload = r.json()

            games = []
            for ev in payload.get("events", []):
                comp = (ev.get("competitions") or [{}])[0]
                competitors = comp.get("competitors") or []

                teams = []
                for c in competitors:
                    team = c.get("team") or {}
                    teams.append({
                        "id": str(team.get("id", "")),
                        "name": team.get("displayName") or team.get("shortDisplayName") or "",
                        "short": team.get("shortDisplayName") or team.get("displayName") or "",
                        "abbrev": team.get("abbreviation") or "",
                        "homeAway": c.get("homeAway", ""),
                        "score": c.get("score", ""),
                    })

                st = (comp.get("status") or {}).get("type") or {}
                broadcasts = []
                for b in comp.get("broadcasts") or []:
                    broadcasts.extend(b.get("names") or [])

                games.append({
                    "id": str(ev.get("id", "")),
                    "date": ev.get("date", ""),
                    "name": ev.get("name", ""),
                    "teams": teams,
                    "state": st.get("state", ""),
                    "completed": bool(st.get("completed")),
                    "detail": st.get("shortDetail") or st.get("detail") or "",
                    "broadcasts": broadcasts[:3],
                })

            return games

        except Exception as exc:
            last_error = exc

    print(f"Scoreboard fetch failed for {start}: {last_error}")
    return None

def main():
    data = json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {}
    old_scores = data.get("fcs_scores") if isinstance(data.get("fcs_scores"), dict) else {}
    scores = dict(old_scores)

    successful_weeks = 0

    for start, end in WEEKS:
        games = fetch_week(start, end)

        # Never erase a previously good week because one API request failed.
        if games is None:
            continue

        scores[start] = games
        successful_weeks += 1

    if successful_weeks:
        data["fcs_scores"] = scores
        data["fcs_scores_updated"] = datetime.now(timezone.utc).isoformat()
        DATA.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"FCS scoreboard repaired/refreshed: {successful_weeks} weeks fetched.")
    else:
        print("No FCS weeks could be fetched; existing cached scores were preserved.")

if __name__ == "__main__":
    main()
