import json
import re
from collections import defaultdict
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA = Path("data.json")
URL = "https://gogriz.com/sports/football/stats/2026"
ROSTER_URL = "https://gogriz.com/sports/football/roster/2026"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GrizHQ/1.0)"}
CATEGORIES = ("passing", "rushing", "receiving", "tackles", "pressure", "special")


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def key(value):
    value = clean(value).upper().replace("’", "'")
    value = re.sub(r"[^A-Z0-9 ]+", " ", value)
    return " ".join(sorted(value.split()))


def soup(url):
    response = requests.get(url, headers=HEADERS, timeout=45)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def candidates(cell):
    values = []
    nodes = [cell] + cell.find_all(["a", "span", "img"])
    for node in nodes:
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
    return list(dict.fromkeys(values))


def roster_map(page):
    result = {}
    for anchor in page.find_all("a", href=True):
        if "/roster/" not in anchor["href"]:
            continue
        for value in candidates(anchor):
            if len(value.split()) >= 2:
                result.setdefault(key(value), value)
    if not result:
        raise RuntimeError("Could not read the official Montana roster")
    return result


def player(cell, roster):
    for value in candidates(cell):
        value = re.sub(r"\b(?:QB|RB|WR|TE|OL|DL|LB|DB|S|CB|FB|K|P|LS)\b", " ", value, flags=re.I)
        value = clean(value)
        if key(value) in roster:
            return roster[key(value)]
    return ""


def headers(table):
    rows = table.find_all("tr")
    for index, row in enumerate(rows[:20]):
        values = [clean(c.get_text(" ", strip=True)).upper() for c in row.find_all(["th", "td"])]
        if any(v == "PLAYER" or v.startswith("PLAYER ") for v in values):
            return values, rows, index
    return [], [], -1


def column(values, *wanted):
    for wanted_name in wanted:
        for index, value in enumerate(values):
            if value == wanted_name or value.startswith(wanted_name + " "):
                return index
    return None


def number(value):
    match = re.search(r"-?\d+(?:\.\d+)?", clean(value).replace(",", ""))
    return float(match.group()) if match else 0.0


def classify(h):
    has = lambda *names: column(h, *names) is not None
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


def parse(table, category, roster, totals):
    h, rows, header_index = headers(table)
    if not h:
        return
    p = column(h, "PLAYER")
    if p is None:
        return
    for row in rows[header_index + 1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) <= p:
            continue
        name = player(cells[p], roster)
        if not name:
            continue
        values = [clean(c.get_text(" ", strip=True)) for c in cells]
        def v(*names):
            i = column(h, *names)
            return number(values[i]) if i is not None and i < len(values) else 0.0
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
        bucket = totals[category][key(name)]
        bucket["player"] = name
        for metric, amount in metrics.items():
            bucket[metric] += amount


def output(totals):
    result = {c: [] for c in CATEGORIES}
    order = {"passing": "yds", "rushing": "yds", "receiving": "yds", "tackles": "tot", "pressure": "tfl", "special": "made"}
    for category in CATEGORIES:
        rows = sorted(totals[category].values(), key=lambda r: (-r[order[category]], r["player"]))
        for row in [r for r in rows if r[order[category]] > 0][:5]:
            if category == "passing":
                line = f'{int(row["cmp"])} CMP • {int(row["yds"])} YDS • {int(row["td"])} TD • {int(row["int"])} INT'; extra = ""
            elif category == "rushing":
                line = f'{int(row["att"])} CAR • {int(row["yds"])} YDS • {int(row["td"])} TD'; extra = ""
            elif category == "receiving":
                line = f'{int(row["rec"])} REC • {int(row["yds"])} YDS • {int(row["td"])} TD'; extra = ""
            elif category == "tackles":
                line = f'{row["tot"]:.1f} TKL • {row["solo"]:.1f} SOLO'; extra = f'{row["ast"]:.1f} AST'
            elif category == "pressure":
                line = f'{row["tfl"]:.1f} TFL • {row["sacks"]:.1f} SACK • {row["ff"]:.1f} FF'; extra = f'{row["int"]:.1f} INT'
            else:
                line = f'{int(row["made"])} MADE • {int(row["attempts"])} ATT'; extra = f'{int(row["punts"])} PUNTS • {int(row["yds"])} YDS' if row["punts"] else ""
            result[category].append({"player": row["player"], "line": line, "extra": extra})
    return result


def main():
    roster = roster_map(soup(ROSTER_URL))
    totals = {c: defaultdict(lambda: defaultdict(float)) for c in CATEGORIES}
    page = soup(URL)
    for table in page.find_all("table"):
        h, _, _ = headers(table)
        category = classify(h)
        if category:
            parse(table, category, roster, totals)
    leaders = output(totals)
    data = json.loads(DATA.read_text(encoding="utf-8"))
    stats = data.setdefault("stats", {})
    stats["leaders"] = leaders
    stats["leaders_source"] = "Official GoGriz 2026 cumulative statistics, restricted to official Montana roster"
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Published official-roster-filtered cumulative Montana player leaders")


if __name__ == "__main__":
    main()
