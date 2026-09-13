import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA = Path("data.json")
URL = "https://gogriz.com/sports/football/stats/2026"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GrizHQ/1.0; +https://grizhq.com)"}

CATEGORIES = ("passing", "rushing", "receiving", "tackles", "pressure", "special")
BAD_PLAYERS = {
    "player", "players", "total", "opponents", "opponent", "montana",
    "team", "team totals", "individual", "individual statistics"
}


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def category_for(table):
    headers = [clean(x.get_text(" ", strip=True)).lower() for x in table.find_all("th")]
    header_text = " ".join(headers)
    nearby = []
    node = table
    for _ in range(5):
        node = node.find_previous(["h1", "h2", "h3", "h4", "h5", "h6", "caption", "strong"])
        if not node:
            break
        nearby.append(clean(node.get_text(" ", strip=True)).lower())
    text = " ".join(nearby + [header_text])

    # Prefer explicit section names, then distinctive column combinations.
    for name in CATEGORIES:
        if re.search(rf"\b{name}\b", text):
            return name
    if ("cmp" in text or "comp" in text or "completion" in text) and "att" in text:
        return "passing"
    if "receiving" in text or ("rec" in text and ("long" in text or "yds" in text)):
        return "receiving"
    if "rushing" in text or all(x in text for x in ("att", "gain", "loss")):
        return "rushing"
    if "tackles" in text or ("solo" in text and ("ast" in text or "assist" in text)):
        return "tackles"
    if any(x in text for x in ("sacks", "tfl", "forced fumbles", "passes defended")):
        return "pressure"
    if any(x in text for x in ("punts", "punting", "field goals", "fgm", "fga", "kicking")):
        return "special"
    return None


def parse():
    response = requests.get(URL, headers=HEADERS, timeout=45)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    leaders = {key: [] for key in CATEGORIES}

    for table in soup.find_all("table"):
        category = category_for(table)
        if not category:
            continue

        rows = []
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if len(cells) < 3:
                continue
            values_all = [clean(c.get_text(" ", strip=True)) for c in cells]
            player_index = next(
                (i for i, value in enumerate(values_all[:3])
                 if re.search(r"[A-Za-z]", value)
                 and value.lower() not in BAD_PLAYERS
                 and value.lower() not in {"gp", "no", "yds", "att", "gain", "loss", "net", "avg", "td", "long"}),
                None,
            )
            if player_index is None:
                continue
            player = values_all[player_index]
            if player.lower() in BAD_PLAYERS or player.lower().startswith("opponent"):
                continue
            values = [v for v in values_all[player_index + 1:] if v]
            if not values:
                continue
            rows.append({"player": player, "line": " • ".join(values[:6]), "extra": ""})

        # Keep the official ordering and avoid duplicate table fragments.
        seen = set()
        for row in rows:
            key = row["player"].lower()
            if key not in seen and len(leaders[category]) < 4:
                leaders[category].append(row)
                seen.add(key)

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
