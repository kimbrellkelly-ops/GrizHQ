import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA = Path("data.json")
URLS = [
    "https://www.cbssports.com/college-football/teams/MT/montana-grizzlies/stats/",
    "https://new.cbssports.com/college-football/teams/MT/montana-grizzlies/stats/",
]
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
OFFENSE = ("passing", "rushing", "receiving")
ALL = OFFENSE + ("tackles", "pressure", "special")


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
    for row_index, row in enumerate(rows[:20]):
        headers = [norm(cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"])]
        if any(h == "PLAYER" or h.startswith("PLAYER ") for h in headers) and len(headers) >= 3:
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

    for candidate in candidates:
        candidate = re.sub(r"\b(?:QB|RB|WR|TE|OL|DL|LB|DB|S|CB|FB|K|P|LS)\b", " ", candidate, flags=re.I)
        candidate = clean(candidate)
        if candidate.lower() in {"player", "player on team", "team", "opponents", "total", "totals"}:
            continue
        words = candidate.split()
        if len(words) >= 4:
            words = words[-3:]
            if len(words) == 3 and re.fullmatch(r"[A-Za-z]\\.?", words[0]):
                words = words[1:]
        if len(words) >= 2:
            return " ".join(words)
    return ""


def parse_table(table, category):
    headers, rows, header_row = table_header(table)
    if not headers:
        return []
    player_column = next((i for i, h in enumerate(headers) if h == "PLAYER" or h.startswith("PLAYER ")), None)
    if player_column is None:
        return []

    def value(values, *names):
        i = index_of(headers, *names)
        return values[i] if i is not None and i < len(values) else ""

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
    data = json.loads(DATA.read_text(encoding="utf-8"))
    previous = data.get("stats", {}).get("leaders", {})
    leaders = {name: [] for name in ALL}
    source_used = None

    for url in URLS:
        try:
            response = requests.get(url, headers=HEADERS, timeout=45)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            candidate = {name: [] for name in OFFENSE}
            for table in soup.find_all("table"):
                headers, _, _ = table_header(table)
                if not headers:
                    continue
                if index_of(headers, "CMP", "COMP") is not None and index_of(headers, "ATT") is not None and index_of(headers, "YDS") is not None:
                    candidate["passing"] = parse_table(table, "passing")[:5]
                elif index_of(headers, "REC", "RECEPTIONS") is not None and index_of(headers, "YDS") is not None:
                    candidate["receiving"] = parse_table(table, "receiving")[:5]
                elif index_of(headers, "ATT") is not None and index_of(headers, "YDS") is not None and index_of(headers, "AVG") is not None:
                    candidate["rushing"] = parse_table(table, "rushing")[:5]
            if all(candidate[name] for name in OFFENSE):
                leaders.update(candidate)
                source_used = url
                break
        except requests.RequestException as exc:
            print(f"Source unavailable: {url}: {exc}")

    if source_used is None:
        if not all(previous.get(name) for name in OFFENSE):
            raise RuntimeError("No complete verified offensive leaders were available from CBS or existing data")
        for name in OFFENSE:
            leaders[name] = previous[name]
        source_used = "existing verified CBS offensive leaders"
        print("CBS unavailable; preserved existing offensive leaders")

    # Never carry forward the known-bad opponent defensive/special-teams rows.
    # These categories will remain empty until a separate verified Montana
    # box-score aggregation is installed.
    for name in ("tackles", "pressure", "special"):
        leaders[name] = []

    stats = data.setdefault("stats", {})
    stats["leaders"] = leaders
    stats["leaders_source"] = source_used
    stats["leaders_updated"] = data.get("updated")
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Updated verified offensive leaders; cleared unverified defensive and special-teams leaders")


if __name__ == "__main__":
    main()
