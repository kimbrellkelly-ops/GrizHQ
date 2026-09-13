import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA = Path("data.json")
URL = "https://gogriz.com/sports/football/stats/2026"
HEADERS = {"User-Agent": "GrizHQ/1.0 (+https://grizhq.com)"}


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def parse():
    response = requests.get(URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    leaders = {"passing": [], "rushing": [], "receiving": [], "tackles": [], "pressure": [], "special": []}

    for table in soup.find_all("table"):
        headers = [clean(x.get_text(" ", strip=True)).lower() for x in table.find_all("th")]
        if not headers:
            continue
        text = " ".join(headers)
        category = None

        # Sidearm has changed the exact header labels over time. Use broad,
        # column-based detection instead of relying on one page wording.
        if (("cmp" in text or "comp" in text or "completion" in text) and "att" in text) or "passing yards" in text:
            category = "passing"
        elif "rushing yards" in text or all(x in text for x in ("att", "gain", "loss")) or all(x in text for x in ("att", "net", "td")):
            category = "rushing"
        elif "receiving yards" in text or ("rec" in text and ("long" in text or "yds" in text)):
            category = "receiving"
        elif ("solo" in text and ("ast" in text or "assist" in text)) or "tackles" in text or "tot" in text and "solo" in text:
            category = "tackles"
        elif "sacks" in text or "tfl" in text or "forced fumbles" in text or "interceptions" in text and "passes defended" in text:
            category = "pressure"
        elif ("punts" in text or "punting" in text or "field goals" in text or "fgm" in text or "fga" in text or "kicking" in text):
            category = "special"

        if not category:
            continue

        rows = []
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if len(cells) < 3:
                continue
            player_cell = cells[1] if len(cells) > 1 else cells[0]
            player = clean(player_cell.get_text(" ", strip=True))
            if not player or player.lower() in {"player", "total", "opponents"} or not re.search(r"[A-Za-z]", player):
                continue
            values = [clean(c.get_text(" ", strip=True)) for c in cells[2:]]
            rows.append((player, values))

        for player, values in rows[:4]:
            line = " • ".join(v for v in values[:5] if v)
            leaders[category].append({"player": player, "line": line, "extra": ""})

    if not any(leaders.values()):
        raise RuntimeError("No player-stat tables were detected on official page")
    return leaders


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    stats = data.setdefault("stats", {})
    leaders = parse()
    old = stats.setdefault("leaders", {})
    for key, value in leaders.items():
        if value:
            old[key] = value
    stats["leaders"] = old
    stats["leaders_source"] = URL
    stats["leaders_updated"] = data.get("updated")
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Official player-stat categories refreshed:", ", ".join(k for k, v in leaders.items() if v))


if __name__ == "__main__":
    main()
