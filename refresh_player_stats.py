import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA = Path("data.json")
URL = "https://www.cbssports.com/college-football/teams/MT/montana-grizzlies/stats/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GrizHQ/1.0)"}
CATEGORIES = ("passing", "rushing", "receiving", "tackles", "pressure", "special")


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def norm(value):
    return re.sub(r"[^A-Z0-9%]+", " ", clean(value).upper()).strip()


def field_index(headers, *wanted):
    for target in wanted:
        for index, header in enumerate(headers):
            if header == target or header.startswith(target + " "):
                return index
    return None


def get_headers(table):
    rows = table.find_all("tr")
    for row_index, row in enumerate(rows[:12]):
        headers = [norm(cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"])]
        if any(header == "PLAYER" or header.startswith("PLAYER ") for header in headers) and len(headers) >= 3:
            return headers, rows, row_index
    return [], rows, -1


def has(headers, *names):
    return any(field_index(headers, name) is not None for name in names)


def categories_for(headers):
    result = []
    if has(headers, "ATT PASS", "PASS ATTEMPTS") and has(headers, "CMP", "COMP") and has(headers, "YDS PASS", "PASSING YARDS"):
        result.append("passing")
    if has(headers, "ATT RUSH", "RUSHING ATTEMPTS", "ATT") and has(headers, "YDS RUSH", "RUSHING YARDS", "YDS") and has(headers, "AVG"):
        result.append("rushing")
    if has(headers, "REC", "RECEPTIONS") and has(headers, "YDS REC", "RECEIVING YARDS", "YDS"):
        result.append("receiving")
    if has(headers, "TOT", "TOTAL") and has(headers, "SOLO") and has(headers, "AST", "ASSIST"):
        result.append("tackles")
    if has(headers, "TFL", "TACKLES FOR LOSS") or has(headers, "SACK", "SACKS"):
        result.append("pressure")
    if has(headers, "PUNTS", "PUNT ATTEMPTS") or has(headers, "FGM", "FIELD GOALS MADE") or has(headers, "FGA", "FIELD GOAL ATTEMPTS"):
        result.append("special")
    return list(dict.fromkeys(result))


def player_name(cell):
    candidates = []
    text = clean(cell.get_text(" ", strip=True))
    if text:
        candidates.append(text)
    for element in cell.find_all(["a", "span"]):
        for attribute in ("title", "aria-label", "data-name"):
            candidate = clean(element.get(attribute, ""))
            if candidate:
                candidates.append(candidate)
        candidate = clean(element.get_text(" ", strip=True))
        if candidate:
            candidates.append(candidate)

    position_pattern = r"\b(?:QB|RB|WR|TE|OL|DL|LB|DB|S|CB|FB|K|P|LS)\b"
    cleaned = []
    for candidate in candidates:
        pieces = [clean(piece) for piece in re.split(position_pattern, candidate, flags=re.I)]
        pieces = [piece for piece in pieces if len(piece.split()) >= 2]
        cleaned.extend(pieces or [candidate])

    for candidate in sorted(cleaned, key=len, reverse=True):
        candidate = re.sub(r"^\s*[A-Z0-9]+[.)]?\s+", "", candidate)
        if candidate and candidate.lower() not in {"player", "team", "opponents", "total", "totals"}:
            return candidate
    return ""


def parse_table(table, category):
    headers, rows, header_row = get_headers(table)
    if not headers:
        return []
    player_column = next((i for i, header in enumerate(headers) if header == "PLAYER" or header.startswith("PLAYER ")), None)
    if player_column is None:
        return []

    def value(values, *names):
        index = field_index(headers, *names)
        return values[index] if index is not None and index < len(values) else ""

    result = []
    for row in rows[header_row + 1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) <= player_column:
            continue
        player = player_name(cells[player_column])
        if not player:
            continue
        values = [clean(cell.get_text(" ", strip=True)) for cell in cells]
        if category == "passing":
            line = f'{value(values, "CMP", "COMP") or "0"} CMP • {value(values, "YDS PASS", "PASSING YARDS", "YDS") or "0"} YDS • {value(values, "TD") or "0"} TD • {value(values, "INT") or "0"} INT'
            extra = f'Long: {value(values, "LONG")}' if value(values, "LONG") else ""
        elif category == "rushing":
            line = f'{value(values, "ATT RUSH", "RUSHING ATTEMPTS", "ATT") or "0"} CAR • {value(values, "YDS RUSH", "RUSHING YARDS", "YDS") or "0"} YDS • {value(values, "TD") or "0"} TD'
            extra = f'Avg: {value(values, "AVG")}' if value(values, "AVG") else ""
        elif category == "receiving":
            line = f'{value(values, "REC", "RECEPTIONS") or "0"} REC • {value(values, "YDS REC", "RECEIVING YARDS", "YDS") or "0"} YDS • {value(values, "TD") or "0"} TD'
            extra = f'Long: {value(values, "LONG")}' if value(values, "LONG") else ""
        elif category == "tackles":
            line = f'{value(values, "TOT", "TOTAL") or "0"} TKL • {value(values, "SOLO") or "0"} SOLO'
            extra = f'{value(values, "AST", "ASSIST") or "0"} AST'
        elif category == "pressure":
            line = f'{value(values, "TFL", "TACKLES FOR LOSS") or "0"} TFL • {value(values, "SACK", "SACKS") or "0"} SACK • {value(values, "FF") or "0"} FF'
            extra = f'{value(values, "INT") or "0"} INT • {value(values, "PBU", "PASS BREAKUPS") or "0"} PBU'
        else:
            punts = value(values, "PUNTS", "PUNT ATTEMPTS")
            made = value(values, "FGM", "FIELD GOALS MADE")
            attempts = value(values, "FGA", "FIELD GOAL ATTEMPTS")
            if punts:
                line = f'{punts} PUNTS • {value(values, "YDS", "PUNT YARDS") or "0"} YDS • {value(values, "AVG") or "0"} AVG'
                extra = f'Long: {value(values, "LONG")}' if value(values, "LONG") else ""
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
    leaders = {category: [] for category in CATEGORIES}

    for table in soup.find_all("table"):
        headers, _, _ = get_headers(table)
        for category in categories_for(headers):
            parsed = parse_table(table, category)
            if parsed and not leaders[category]:
                leaders[category] = parsed[:5]

    missing = [category for category in CATEGORIES if not leaders[category]]
    if missing:
        raise RuntimeError("Structured stats source did not provide categories: " + ", ".join(missing))

    stats["leaders"] = leaders
    stats["leaders_source"] = URL
    stats["leaders_updated"] = data.get("updated")
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Player leaders refreshed from structured CBS stats:", ", ".join(CATEGORIES))


if __name__ == "__main__":
    main()
