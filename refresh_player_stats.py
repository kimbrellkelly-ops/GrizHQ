import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA = Path("data.json")
SOURCE = "https://gogriz.com/sports/football/stats/2026"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
}
CATEGORIES = ("passing", "rushing", "receiving", "tackles", "pressure", "special")


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def norm(value):
    return re.sub(r"[^A-Z0-9%/.-]+", " ", clean(value).upper()).strip()


def header_row(table):
    rows = table.find_all("tr")
    for index, row in enumerate(rows[:20]):
        headers = [norm(cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"])]
        if any(h == "PLAYER" or h.startswith("PLAYER ") for h in headers):
            return headers, rows, index
    return [], [], -1


def column(headers, *names):
    for wanted in names:
        for index, value in enumerate(headers):
            if value == wanted or value.startswith(wanted + " "):
                return index
    return None


def player_name(cell):
    candidates = []
    for node in [cell] + cell.find_all(["a", "span"]):
        for attr in ("data-name", "aria-label", "title", "alt"):
            value = clean(node.get(attr, ""))
            if value:
                candidates.append(value)
        text = clean(node.get_text(" ", strip=True))
        if text:
            candidates.append(text)

    for value in candidates:
        value = re.sub(r"\b(?:QB|RB|WR|TE|OL|DL|LB|DB|S|CB|FB|K|P|LS)\b", " ", value, flags=re.I)
        value = clean(value)
        if value.lower() in {"player", "player on team", "team", "total", "opponents", "totals"}:
            continue
        # GoGriz normally uses Last, First. Keep that exact display format.
        if "," in value and len(value.split()) >= 2:
            return value
        words = value.split()
        if len(words) >= 2:
            return " ".join(words[-3:]) if len(words) > 3 else value
    return ""


def classify(headers):
    has = lambda *names: column(headers, *names) is not None
    if has("CMP", "COMP") and has("ATT") and has("YDS") and has("TD"):
        return "passing"
    if has("REC", "RECEPTIONS") and has("YDS") and has("TD"):
        return "receiving"
    if has("CAR", "ATT") and has("YDS") and has("TD") and has("AVG"):
        return "rushing"
    if has("SOLO") and has("AST") and has("TOT"):
        return "tackles"
    if has("TFL") or (has("SACK") and has("FF")):
        return "pressure"
    if has("PUNTS") or has("FGM") or has("FGA") or has("XPM") or has("XPA"):
        return "special"
    return None


def parse_table(table, category):
    headers, rows, header_index = header_row(table)
    if not headers:
        return []
    player_index = column(headers, "PLAYER")
    if player_index is None:
        return []

    def value(values, *names):
        index = column(headers, *names)
        return values[index] if index is not None and index < len(values) else ""

    output = []
    for row in rows[header_index + 1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) <= player_index:
            continue
        values = [clean(cell.get_text(" ", strip=True)) for cell in cells]
        player = player_name(cells[player_index])
        if not player:
            continue
        if player.lower() in {"total", "totals", "opponents", "team"}:
            continue

        if category == "passing":
            line = f'{value(values, "CMP", "COMP") or "0"} CMP • {value(values, "YDS") or "0"} YDS • {value(values, "TD") or "0"} TD • {value(values, "INT") or "0"} INT'
            extra = f'Long: {value(values, "LONG")}' if value(values, "LONG") else ""
        elif category == "rushing":
            line = f'{value(values, "CAR", "ATT") or "0"} CAR • {value(values, "YDS") or "0"} YDS • {value(values, "TD") or "0"} TD'
            extra = f'Avg: {value(values, "AVG")}' if value(values, "AVG") else ""
        elif category == "receiving":
            line = f'{value(values, "REC", "RECEPTIONS") or "0"} REC • {value(values, "YDS") or "0"} YDS • {value(values, "TD") or "0"} TD'
            extra = f'Long: {value(values, "LONG")}' if value(values, "LONG") else ""
        elif category == "tackles":
            line = f'{value(values, "TOT") or "0"} TKL • {value(values, "SOLO") or "0"} SOLO'
            extra = f'{value(values, "AST") or "0"} AST'
        elif category == "pressure":
            line = f'{value(values, "TFL") or "0"} TFL • {value(values, "SACK", "SACKS") or "0"} SACK • {value(values, "FF") or "0"} FF'
            extra = f'{value(values, "INT") or "0"} INT • {value(values, "PBU", "PB") or "0"} PBU'
        else:
            if has_punts := (column(headers, "PUNTS") is not None):
                line = f'{value(values, "PUNTS") or "0"} PUNTS • {value(values, "YDS") or "0"} YDS • {value(values, "AVG") or "0"} AVG'
                extra = f'Long: {value(values, "LONG")}' if value(values, "LONG") else ""
            else:
                line = f'{value(values, "FGM") or "0"}/{value(values, "FGA") or "0"} FG'
                extra = f'{value(values, "XPM") or "0"}/{value(values, "XPA") or "0"} XP' if column(headers, "XPM") is not None else ""
        output.append({"player": player, "line": line, "extra": extra})
    return output


def main():
    response = requests.get(SOURCE, headers=HEADERS, timeout=45)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    found = {category: [] for category in CATEGORIES}

    for table in soup.find_all("table"):
        headers, _, _ = header_row(table)
        category = classify(headers)
        if not category:
            continue
        rows = parse_table(table, category)
        # Keep the richest table for each category. Never merge opponent and
        # Montana tables, which was the source of the previous bad leaders.
        if len(rows) > len(found[category]):
            found[category] = rows[:5]

    missing = [category for category in CATEGORIES if not found[category]]
    if missing:
        raise RuntimeError("Official Montana cumulative stats missing categories: " + ", ".join(missing))

    data = json.loads(DATA.read_text(encoding="utf-8"))
    stats = data.setdefault("stats", {})
    stats["leaders"] = found
    stats["leaders_source"] = SOURCE
    stats["leaders_updated"] = data.get("updated")
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Updated all player-leader categories from official Montana cumulative statistics")


if __name__ == "__main__":
    main()
