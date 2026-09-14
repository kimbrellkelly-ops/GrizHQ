import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA = Path("data.json")
URL = "https://www.cbssports.com/college-football/teams/MT/montana-grizzlies/stats/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GrizHQ/1.0)"}


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def norm(value):
    return re.sub(r"[^A-Z0-9%]+", " ", clean(value).upper()).strip()


def index_of(headers, *wanted):
    for wanted_name in wanted:
        for index, header in enumerate(headers):
            if header == wanted_name or header.startswith(wanted_name + " "):
                return index
    return None


def table_header(table):
    rows = table.find_all("tr")
    for row_index, row in enumerate(rows[:15]):
        headers = [norm(cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"])]
        # CBS sometimes renders this as PLAYER, PLAYER ON TEAM, or similar.
        if any(header == "PLAYER" or header.startswith("PLAYER ") for header in headers) and len(headers) >= 3:
            return headers, rows, row_index
    return [], [], -1


def player_name(cell):
    candidates = []
    for node in [cell] + cell.find_all(["a", "span"]):
        for attr in ("data-name", "aria-label", "title"):
            value = clean(node.get(attr, ""))
            if value:
                candidates.append(value)
        value = clean(node.get_text(" ", strip=True))
        if value:
            candidates.append(value)

    positions = {"QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB", "S", "CB", "FB", "K", "P", "LS"}
    for candidate in candidates:
        candidate = re.sub(r"\b(?:QB|RB|WR|TE|OL|DL|LB|DB|S|CB|FB|K|P|LS)\b", " ", candidate, flags=re.I)
        candidate = re.sub(r"^\s*[A-Z0-9]+[.)]?\s+", "", clean(candidate))
        candidate = clean(candidate)
        if candidate.lower() in {"player", "team", "opponents", "total", "totals"}:
            continue
        words = candidate.split()
        if len(words) >= 4:
            # CBS commonly combines abbreviated and full names, e.g.
            # “B. Davis Brooks Davis” or “Ransom-Goelz Landon Ransom-Goelz”.
            words = words[-3:]
            if len(words) == 3 and re.fullmatch(r"[A-Za-z]\.?", words[0]):
                words = words[1:]
        if len(words) >= 2:
            return " ".join(words)
    return ""


def parse_table(table, category):
    headers, rows, header_row = table_header(table)
    if not headers:
        return []
    player_column = next((i for i, header in enumerate(headers) if header == "PLAYER" or header.startswith("PLAYER ")), None)
    if player_column is None:
        return []

    def value(values, *names):
        index = index_of(headers, *names)
        return values[index] if index is not None and index < len(values) else ""

    parsed = []
    for row in rows[header_row + 1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) <= player_column:
            continue
        player = player_name(cells[player_column])
        if not player:
            continue
        values = [clean(cell.get_text(" ", strip=True)) for cell in cells]
        if category == "passing":
            line = f'{value(values, "CMP", "COMP") or "0"} CMP • {value(values, "YDS", "YDS PASS", "PASSING YARDS") or "0"} YDS • {value(values, "TD") or "0"} TD • {value(values, "INT") or "0"} INT'
            extra = f'Long: {value(values, "LONG")}' if value(values, "LONG") else ""
        elif category == "rushing":
            line = f'{value(values, "ATT", "ATT RUSH", "RUSHING ATTEMPTS") or "0"} CAR • {value(values, "YDS", "YDS RUSH", "RUSHING YARDS") or "0"} YDS • {value(values, "TD") or "0"} TD'
            extra = f'Avg: {value(values, "AVG")}' if value(values, "AVG") else ""
        else:
            line = f'{value(values, "REC", "RECEPTIONS") or "0"} REC • {value(values, "YDS", "YDS REC", "RECEIVING YARDS") or "0"} YDS • {value(values, "TD") or "0"} TD'
            extra = f'Long: {value(values, "LONG")}' if value(values, "LONG") else ""
        parsed.append({"player": player, "line": line, "extra": extra})
    return parsed


def main():
    response = requests.get(URL, headers=HEADERS, timeout=45)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    data = json.loads(DATA.read_text(encoding="utf-8"))
    leaders = {"passing": [], "rushing": [], "receiving": [], "tackles": [], "pressure": [], "special": []}

    for table in soup.find_all("table"):
        headers, _, _ = table_header(table)
        if not headers:
            continue
        if index_of(headers, "CMP", "COMP") is not None and index_of(headers, "YDS") is not None and index_of(headers, "ATT") is not None:
            leaders["passing"] = parse_table(table, "passing")[:5]
        elif index_of(headers, "REC", "RECEPTIONS") is not None and index_of(headers, "YDS") is not None:
            leaders["receiving"] = parse_table(table, "receiving")[:5]
        elif index_of(headers, "ATT") is not None and index_of(headers, "YDS") is not None and index_of(headers, "AVG") is not None:
            leaders["rushing"] = parse_table(table, "rushing")[:5]

    missing = [name for name in ("passing", "rushing", "receiving") if not leaders[name]]
    if missing:
        raise RuntimeError("CBS offensive stats missing: " + ", ".join(missing))

    stats = data.setdefault("stats", {})
    stats["leaders"] = leaders
    stats["leaders_source"] = URL + " (CBS verified offense; defensive and special-teams categories withheld until separately verified)"
    stats["leaders_updated"] = data.get("updated")
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Updated CBS Montana offensive leaders; defensive and special teams withheld")


if __name__ == "__main__":
    main()
