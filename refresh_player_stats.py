import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA = Path("data.json")
URL = "https://www.cbssports.com/college-football/teams/MT/montana-grizzlies/stats/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GrizHQ/1.0)"}

# CBS exposes reliable player tables for these categories. Defensive and
# kicking tables are not consistently exposed in the accessible page, so
# they must never be guessed from unrelated tables.
CATEGORIES = ("passing", "rushing", "receiving")


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def norm(value):
    return re.sub(r"[^A-Z0-9%]+", " ", clean(value).upper()).strip()


def index_of(headers, *wanted):
    for target in wanted:
        for i, header in enumerate(headers):
            if header == target or header.startswith(target + " "):
                return i
    return None


def table_headers(table):
    rows = table.find_all("tr")
    for row_index, row in enumerate(rows[:10]):
        headers = [norm(cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"])]
        if any(h == "PLAYER" or h.startswith("PLAYER ") for h in headers):
            return headers, rows, row_index
    return [], rows, -1


def player_name(cell):
    # CBS repeats abbreviated and full names in the same cell, e.g.
    # "K. Ah Yat QB Keali'i Ah Yat QB". Prefer the full-name occurrence.
    candidates = [clean(cell.get_text(" ", strip=True))]
    for node in cell.find_all(["a", "span"]):
        candidates.extend(clean(node.get(attr, "")) for attr in ("title", "aria-label", "data-name"))
        candidates.append(clean(node.get_text(" ", strip=True)))
    candidates = [c for c in candidates if len(c.split()) >= 2]
    if not candidates:
        return ""
    value = max(candidates, key=len)
    value = re.sub(r"\b(?:QB|RB|WR|TE|OL|DL|LB|DB|S|CB|FB|K|P|LS)\b", "", value, flags=re.I)
    value = clean(value)
    value = re.sub(r"^[A-Z]\.\s+", "", value)
    return value


def parse_table(table, category):
    headers, rows, header_row = table_headers(table)
    if not headers:
        return []
    player_i = index_of(headers, "PLAYER")
    if player_i is None:
        return []

    def value(values, *names):
        i = index_of(headers, *names)
        return values[i] if i is not None and i < len(values) else ""

    output = []
    for row in rows[header_row + 1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) <= player_i:
            continue
        name = player_name(cells[player_i])
        if not name or name.lower() in {"team", "opponents", "total", "totals"}:
            continue
        values = [clean(c.get_text(" ", strip=True)) for c in cells]
        if category == "passing":
            line = f'{value(values, "CMP", "COMP") or "0"} CMP • {value(values, "YDS", "YDS PASS", "PASSING YARDS") or "0"} YDS • {value(values, "TD") or "0"} TD • {value(values, "INT") or "0"} INT'
            extra = f'Long: {value(values, "LONG")}' if value(values, "LONG") else ""
        elif category == "rushing":
            line = f'{value(values, "ATT", "ATT RUSH", "RUSHING ATTEMPTS") or "0"} CAR • {value(values, "YDS", "YDS RUSH", "RUSHING YARDS") or "0"} YDS • {value(values, "TD") or "0"} TD'
            extra = f'Avg: {value(values, "AVG")}' if value(values, "AVG") else ""
        else:
            line = f'{value(values, "REC", "RECEPTIONS") or "0"} REC • {value(values, "YDS", "YDS REC", "RECEIVING YARDS") or "0"} YDS • {value(values, "TD") or "0"} TD'
            extra = f'Long: {value(values, "LONG")}' if value(values, "LONG") else ""
        output.append({"player": name, "line": line, "extra": extra})
    return output


def main():
    response = requests.get(URL, headers=HEADERS, timeout=45)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    data = json.loads(DATA.read_text(encoding="utf-8"))
    stats = data.setdefault("stats", {})
    leaders = {category: [] for category in CATEGORIES}

    for table in soup.find_all("table"):
        headers, _, _ = table_headers(table)
        header_text = " ".join(headers)
        if "ATT PASS" in header_text or "PASS ATTEMPTS" in header_text:
            category = "passing"
        elif "ATT RUSH" in header_text or "RUSHING ATTEMPTS" in header_text:
            category = "rushing"
        elif "RECEPTIONS" in header_text or "REC" in headers:
            category = "receiving"
        else:
            continue
        parsed = parse_table(table, category)
        if parsed and not leaders[category]:
            leaders[category] = parsed[:5]

    missing = [category for category in CATEGORIES if not leaders[category]]
    if missing:
        raise RuntimeError("CBS player-stat categories missing: " + ", ".join(missing))

    # Explicitly clear categories that CBS does not expose here. This is
    # preferable to displaying opponent players from a misidentified table.
    existing = stats.get("leaders", {})
    stats["leaders"] = {
        **existing,
        **leaders,
        "tackles": [],
        "pressure": [],
        "special": [],
    }
    stats["leaders_source"] = URL
    stats["leaders_updated"] = data.get("updated")
    stats["leaders_note"] = "CBS Sports supplies offensive leaders. Defensive and special-teams leaders are withheld when the source does not expose reliable Montana player tables."
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Player leaders refreshed from CBS Sports: passing, rushing, receiving")


if __name__ == "__main__":
    main()
