import json
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

DATA = Path("data.json")
BASE = "https://gogriz.com"
SCHEDULE = f"{BASE}/sports/football/schedule/2026"
ROSTER = f"{BASE}/sports/football/roster/2026"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GrizHQ/1.0)"}
CATEGORIES = ("passing", "rushing", "receiving", "tackles", "pressure", "special")


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def key(value):
    value = clean(value).upper().replace("’", "'")
    value = re.sub(r"[^A-Z0-9 ]+", " ", value)
    return " ".join(sorted(value.split()))


def get(url):
    response = requests.get(url, headers=HEADERS, timeout=45)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def name_candidates(cell):
    values = []
    for node in [cell] + cell.find_all(["a", "span", "img"]):
        for attr in ("data-name", "aria-label", "title", "alt"):
            value = clean(node.get(attr, ""))
            if value:
                values.append(value)
        text = clean(node.get_text(" ", strip=True))
        if text:
            values.append(text)
        href = node.get("href", "")
        match = re.search(r"/roster/[^/]+/([^/?#]+)/?", href)
        if match:
            values.append(match.group(1).replace("-", " "))
    return values


def roster_keys(soup):
    result = set()
    for anchor in soup.find_all("a", href=True):
        if "/roster/" not in anchor["href"]:
            continue
        for value in name_candidates(anchor):
            if len(value.split()) >= 2:
                result.add(key(value))
    if not result:
        raise RuntimeError("Could not establish the official Montana roster")
    return result


def player_name(cell, roster):
    for value in name_candidates(cell):
        value = re.sub(r"\b(?:QB|RB|WR|TE|OL|DL|LB|DB|S|CB|FB|K|P|LS)\b", " ", value, flags=re.I)
        value = clean(value)
        if key(value) in roster:
            return value
    return ""


def headers_for(table):
    rows = table.find_all("tr")
    for index, row in enumerate(rows[:20]):
        headers = [clean(cell.get_text(" ", strip=True)).upper() for cell in row.find_all(["th", "td"])]
        if any(h == "PLAYER" or h.startswith("PLAYER ") for h in headers):
            return headers, rows, index
    return [], [], -1


def col(headers, *wanted):
    for name in wanted:
        for index, value in enumerate(headers):
            if value == name or value.startswith(name + " "):
                return index
    return None


def number(value):
    value = clean(value).replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", value)
    return float(match.group()) if match else 0.0


def classify(headers):
    has = lambda *names: col(headers, *names) is not None
    if has("CMP", "COMP") and has("ATT") and has("YDS") and has("TD"):
        return "passing"
    if has("REC", "RECEPTIONS") and has("YDS") and has("TD"):
        return "receiving"
    if has("CAR", "ATT") and has("YDS") and has("TD"):
        return "rushing"
    if has("SOLO") and has("AST") and has("TOT"):
        return "tackles"
    if has("TFL") or has("SACK", "SACKS") or has("FF"):
        return "pressure"
    if has("PUNTS") or has("FGM") or has("FGA") or has("XPM") or has("XPA"):
        return "special"
    return None


def parse_table(table, category, roster, totals):
    headers, rows, header_index = headers_for(table)
    if not headers:
        return
    player_index = col(headers, "PLAYER")
    if player_index is None:
        return
    for row in rows[header_index + 1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) <= player_index:
            continue
        player = player_name(cells[player_index], roster)
        if not player:
            continue
        values = [clean(cell.get_text(" ", strip=True)) for cell in cells]
        def v(*names):
            index = col(headers, *names)
            return number(values[index]) if index is not None and index < len(values) else 0.0
        if category == "passing":
            metrics = {"cmp": v("CMP", "COMP"), "yds": v("YDS"), "td": v("TD"), "int": v("INT")}
        elif category == "rushing":
            metrics = {"att": v("CAR", "ATT"), "yds": v("YDS"), "td": v("TD")}
        elif category == "receiving":
            metrics = {"rec": v("REC", "RECEPTIONS"), "yds": v("YDS"), "td": v("TD")}
        elif category == "tackles":
            metrics = {"tot": v("TOT"), "solo": v("SOLO"), "ast": v("AST")}
        elif category == "pressure":
            metrics = {"tfl": v("TFL"), "sacks": v("SACK", "SACKS"), "ff": v("FF"), "int": v("INT")}
        else:
            metrics = {"made": v("FGM", "XPM"), "attempts": v("FGA", "XPA"), "punts": v("PUNTS"), "yds": v("YDS")}
        bucket = totals[category][key(player)]
        bucket["player"] = player
        for metric, amount in metrics.items():
            bucket[metric] += amount


def format_leaders(totals):
    output = {category: [] for category in CATEGORIES}
    sort_fields = {"passing": "yds", "rushing": "yds", "receiving": "yds", "tackles": "tot", "pressure": "tfl", "special": "made"}
    for category in CATEGORIES:
        field = sort_fields[category]
        rows = sorted(totals[category].values(), key=lambda row: (-row[field], row["player"]))
        rows = [row for row in rows if row[field] > 0]
        for row in rows[:5]:
            if category == "passing":
                line = f'{int(row["cmp"])} CMP • {int(row["yds"])} YDS • {int(row["td"])} TD • {int(row["int"])} INT'
                extra = ""
            elif category == "rushing":
                line = f'{int(row["att"])} CAR • {int(row["yds"])} YDS • {int(row["td"])} TD'
                extra = ""
            elif category == "receiving":
                line = f'{int(row["rec"])} REC • {int(row["yds"])} YDS • {int(row["td"])} TD'
                extra = ""
            elif category == "tackles":
                line = f'{row["tot"]:.1f} TKL • {row["solo"]:.1f} SOLO'
                extra = f'{row["ast"]:.1f} AST'
            elif category == "pressure":
                line = f'{row["tfl"]:.1f} TFL • {row["sacks"]:.1f} SACK • {row["ff"]:.1f} FF'
                extra = f'{row["int"]:.1f} INT'
            else:
                line = f'{int(row["made"])} MADE • {int(row["attempts"])} ATT'
                extra = f'{int(row["punts"])} PUNTS • {int(row["yds"])} YDS' if row["punts"] else ""
            output[category].append({"player": row["player"], "line": line, "extra": extra})
    return output


def main():
    roster = roster_keys(get(ROSTER))
    schedule = get(SCHEDULE)
    boxscores = []
    for anchor in schedule.find_all("a", href=True):
        href = urljoin(BASE, anchor["href"])
        if "/stats/2026/" in href and "/boxscore/" in href and href not in boxscores:
            boxscores.append(href)
    if not boxscores:
        raise RuntimeError("Could not find official 2026 Montana box-score links")

    totals = {category: defaultdict(lambda: defaultdict(float)) for category in CATEGORIES}
    for url in boxscores:
        soup = get(url)
        for table in soup.find_all("table"):
            headers, _, _ = headers_for(table)
            category = classify(headers)
            if category:
                parse_table(table, category, roster, totals)

    leaders = format_leaders(totals)
    missing = [category for category in CATEGORIES if not leaders[category]]
    if missing:
        raise RuntimeError("Official Montana box-score aggregation missing: " + ", ".join(missing))

    data = json.loads(DATA.read_text(encoding="utf-8"))
    stats = data.setdefault("stats", {})
    stats["leaders"] = leaders
    stats["leaders_source"] = "Official Montana roster + 2026 Montana box scores"
    stats["leaders_updated"] = data.get("updated")
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Aggregated verified Montana player leaders from {len(boxscores)} official box scores")


if __name__ == "__main__":
    main()
