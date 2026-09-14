import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA = Path("data.json")
URL = "https://www.cbssports.com/college-football/teams/MT/montana-grizzlies/stats/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GrizHQ/1.0)"}
OFFENSE = ("passing", "rushing", "receiving")
ALL_CATEGORIES = OFFENSE + ("tackles", "pressure", "special")


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
        if any(h == "PLAYER" or h.startswith("PLAYER ") for h in headers) and len(headers) >= 3:
            return headers, rows, row_index
    return [], rows, -1


def categories_for(headers):
    result = []
    if field_index(headers, "ATT PASS", "PASS ATTEMPTS") is not None and field_index(headers, "CMP", "COMP") is not None and field_index(headers, "YDS PASS", "PASSING YARDS") is not None:
        result.append("passing")
    if field_index(headers, "ATT RUSH", "RUSHING ATTEMPTS", "ATT") is not None and field_index(headers, "YDS RUSH", "RUSHING YARDS", "YDS") is not None and field_index(headers, "AVG") is not None:
        result.append("rushing")
    if field_index(headers, "REC", "RECEPTIONS") is not None and field_index(headers, "YDS REC", "RECEIVING YARDS", "YDS") is not None:
        result.append("receiving")
    return result


def player_name(cell):
    candidates = []
    text = clean(cell.get_text(" ", strip=True))
    if text:
        candidates.append(text)
    for element in cell.find_all(["a", "span"]):
        for attribute in ("title", "aria-label", "data-name"):
            value = clean(element.get(attribute, ""))
            if value:
                candidates.append(value)
        value = clean(element.get_text(" ", strip=True))
        if value:
            candidates.append(value)

    for candidate in candidates:
        candidate = re.sub(r"\b(?:QB|RB|WR|TE|OL|DL|LB|DB|S|CB|FB|K|P|LS)\b", "", candidate, flags=re.I)
        candidate = re.sub(r"^\s*[A-Z0-9]+[.)]?\s+", "", clean(candidate))
        if candidate.lower() in {"player", "team", "opponents", "total", "totals"}:
            continue
        words = candidate.split()
        if len(words) >= 2:
            # CBS sometimes exposes both the displayed name and the accessible name,
            # producing strings such as "Davis Brooks Davis". Keep the first pair.
            if len(words) % 2 == 0 and words[: len(words) // 2] == words[len(words) // 2 :]:
                words = words[: len(words) // 2]
            if len(words) >= 4 and words[-2:] == words[:2]:
                words = words[:2]
            return " ".join(words)
    return ""


def parse_table(table, category):
    headers, rows, header_row = get_headers(table)
    if not headers:
        return []
    player_column = next((i for i, h in enumerate(headers) if h == "PLAYER" or h.startswith("PLAYER ")), None)
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
        else:
            line = f'{value(values, "REC", "RECEPTIONS") or "0"} REC • {value(values, "YDS REC", "RECEIVING YARDS", "YDS") or "0"} YDS • {value(values, "TD") or "0"} TD'
            extra = f'Long: {value(values, "LONG")}' if value(values, "LONG") else ""
        result.append({"player": player, "line": line, "extra": extra})
    return result


def main():
    response = requests.get(URL, headers=HEADERS, timeout=45)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    data = json.loads(DATA.read_text(encoding="utf-8"))
    stats = data.setdefault("stats", {})
    leaders = {category: [] for category in ALL_CATEGORIES}

    for table in soup.find_all("table"):
        headers, _, _ = get_headers(table)
        for category in categories_for(headers):
            parsed = parse_table(table, category)
            if parsed and not leaders[category]:
                leaders[category] = parsed[:5]

    missing = [category for category in OFFENSE if not leaders[category]]
    if missing:
        raise RuntimeError("CBS offensive stats missing: " + ", ".join(missing))

    # Defensive and special-teams values previously came from opponent tables.
    # Do not publish them until they are sourced from verified Montana box scores.
    stats["leaders"] = leaders
    stats["leaders_source"] = URL + " (offense only; defense/special teams pending verified source)"
    stats["leaders_updated"] = data.get("updated")
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Refreshed Montana offensive leaders; withheld unverified defense/special teams")


if __name__ == "__main__":
    main()
