import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA = Path("data.json")
URL = "https://gogriz.com/sports/football/stats/2026"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GrizHQ/1.0)"}
CATEGORIES = ("passing", "rushing", "receiving", "tackles", "pressure", "special")


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def norm(value):
    return re.sub(r"[^A-Z0-9%]+", " ", clean(value).upper()).strip()


def first_index(headers, *names):
    for wanted in names:
        for index, header in enumerate(headers):
            if header == wanted or header.startswith(wanted + " "):
                return index
    return None


def get_headers(table):
    rows = table.find_all("tr")
    for row_index, row in enumerate(rows[:12]):
        headers = [norm(cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"])]
        if "PLAYER" in headers and len(headers) >= 3:
            return headers, rows, row_index
    return [], rows, -1


def categories_for(headers):
    header_set = set(headers)
    joined = " ".join(headers)
    result = []
    if ("CMP" in header_set or "COMP" in header_set) and "ATT" in header_set and ("YDS" in header_set or "YARD" in header_set):
        result.append("passing")
    if "ATT" in header_set and ("GAIN" in header_set or "NET" in header_set) and ("LOSS" in header_set or "AVG" in header_set):
        result.append("rushing")
    if ("REC" in header_set or "RECEPTIONS" in header_set or "NO" in header_set) and ("YDS" in header_set or "YARD" in header_set):
        result.append("receiving")
    if "SOLO" in header_set and ("AST" in header_set or "ASSIST" in header_set) and ("TOT" in header_set or "TOTAL" in header_set):
        result.extend(["tackles", "pressure"])
    if "PUNTS" in header_set or "FGM" in header_set or "FGA" in header_set or ("KICK" in joined and "YDS" in header_set):
        result.append("special")
    return list(dict.fromkeys(result))


def player_name(cell):
    value = clean(cell.get_text(" ", strip=True))
    if value:
        return value
    for element in cell.find_all(["a", "img"]):
        for attribute in ("title", "aria-label", "alt"):
            candidate = clean(element.get(attribute, ""))
            if candidate:
                return candidate
        href = element.get("href", "")
        match = re.search(r"/roster/[^/]+/([^/?#]+)/?", href)
        if match:
            return clean(match.group(1).replace("-", " "))
    return ""


def parse_table(table, category):
    headers, rows, header_row = get_headers(table)
    if not headers:
        return []
    player_column = headers.index("PLAYER")
    result = []
    for row in rows[header_row + 1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) <= player_column:
            continue
        player = player_name(cells[player_column])
        if not player or player.lower() in {"player", "total", "opponents", "team", "montana"}:
            continue
        values = [clean(cell.get_text(" ", strip=True)) for cell in cells]

        def value(*names):
            index = first_index(headers, *names)
            return values[index] if index is not None and index < len(values) else ""

        if category == "passing":
            line = f'{value("CMP", "COMP") or "0"} CMP • {value("YDS", "YARD") or "0"} YDS • {value("TD") or "0"} TD • {value("INT") or "0"} INT'
            extra = f'Long: {value("LONG")}' if value("LONG") else ""
        elif category == "rushing":
            line = f'{value("ATT", "CAR", "CARRIES") or "0"} CAR • {value("NET", "YDS", "YARD") or "0"} YDS • {value("TD") or "0"} TD'
            extra = f'Avg: {value("AVG")}' if value("AVG") else ""
        elif category == "receiving":
            line = f'{value("REC", "RECEPTIONS", "NO") or "0"} REC • {value("YDS", "YARD") or "0"} YDS • {value("TD") or "0"} TD'
            extra = f'Long: {value("LONG")}' if value("LONG") else ""
        elif category == "tackles":
            line = f'{value("TOT", "TKL", "TOTAL") or "0"} TKL • {value("SOLO") or "0"} SOLO'
            extra = f'{value("AST", "ASSIST") or "0"} AST'
        elif category == "pressure":
            line = f'{value("TFL YDS", "TFL") or "0"} TFL • {value("SACK YDS", "SACK", "SACKS") or "0"} SACK • {value("FF") or "0"} FF'
            extra = f'{value("INT") or "0"} INT • {value("BRUP", "PBU") or "0"} PBU'
        else:
            punts = value("PUNTS")
            made = value("FGM", "MADE")
            attempts = value("FGA", "ATT")
            if punts:
                line = f'{punts} PUNTS • {value("YDS", "YARD") or "0"} YDS • {value("AVG") or "0"} AVG'
                extra = f'Long: {value("LONG")}' if value("LONG") else ""
            elif made or attempts:
                line, extra = f'{made or "0"}/{attempts or "0"} FG', ""
            else:
                continue
        result.append({"player": player, "line": line, "extra": extra})
    return result


def main():
    response = requests.get(URL, headers=HEADERS, timeout=45)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    data = json.loads(DATA.read_text(encoding="utf-8"))
    stats = data.setdefault("stats", {})
    existing = stats.get("leaders", {})
    leaders = {category: [] for category in CATEGORIES}

    for table in soup.find_all("table"):
        headers, _, _ = get_headers(table)
        for category in categories_for(headers):
            parsed = parse_table(table, category)
            if parsed and not leaders[category]:
                leaders[category] = parsed[:5]

    # Never erase a working category because a provider temporarily changes markup.
    for category in CATEGORIES:
        if not leaders[category] and existing.get(category):
            leaders[category] = existing[category]

    available = [category for category in CATEGORIES if leaders[category]]
    if not available:
        raise RuntimeError("No usable player-stat tables were found")

    stats["leaders"] = leaders
    stats["leaders_source"] = URL
    stats["leaders_updated"] = data.get("updated")
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Player-stat categories refreshed or safely preserved:", ", ".join(available))


if __name__ == "__main__":
    main()
