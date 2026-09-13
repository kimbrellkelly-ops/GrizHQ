import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA = Path("data.json")
STATS_URL = "https://gogriz.com/sports/football/stats/2026"
ROSTER_URL = "https://gogriz.com/sports/football/roster/2026"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GrizHQ/1.0)"}
CATEGORIES = ("passing", "rushing", "receiving", "tackles", "pressure", "special")


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def norm(value):
    return re.sub(r"[^a-z0-9]+", "-", clean(value).lower()).strip("-")


def header_info(table):
    rows = table.find_all("tr")
    for row_index, row in enumerate(rows[:12]):
        headers = [clean(cell.get_text(" ", strip=True)).upper() for cell in row.find_all(["th", "td"])]
        if "PLAYER" in headers and len(headers) >= 3:
            return headers, rows, row_index
    return [], [], -1


def first_index(headers, *names):
    for wanted in names:
        for index, header in enumerate(headers):
            if header == wanted or header.startswith(wanted + " "):
                return index
    return None


def categories_for(headers):
    joined = " ".join(headers)
    result = []
    if ("CMP" in headers or "COMP" in headers) and "ATT" in headers and "YDS" in headers:
        result.append("passing")
    if "ATT" in headers and ("GAIN" in headers or "NET" in headers) and ("LOSS" in headers or "AVG" in headers):
        result.append("rushing")
    if ("REC" in headers or "RECEPTIONS" in headers or "NO" in headers) and "YDS" in headers:
        result.append("receiving")
    if "SOLO" in headers and ("AST" in headers or "ASSIST" in headers) and ("TOT" in headers or "TOTAL" in headers):
        result.extend(["tackles", "pressure"])
    if "PUNTS" in headers or "FGM" in headers or "FGA" in headers or ("KICK" in joined and "YDS" in headers):
        result.append("special")
    return list(dict.fromkeys(result))


def roster_identities(soup):
    identities = set()
    for element in soup.find_all(["a", "td", "span"]):
        href = element.get("href", "")
        text = clean(element.get_text(" ", strip=True))
        candidates = [text, element.get("title", ""), element.get("aria-label", "")]
        match = re.search(r"/player/([^/?#]+)/?", href)
        if match:
            candidates.append(match.group(1).replace("-", " "))
        for candidate in candidates:
            key = norm(candidate)
            if key and len(key.split("-")) >= 2:
                identities.add(key)
    return identities


def player_identity(cell):
    text = clean(cell.get_text(" ", strip=True))
    candidates = [text, cell.get("title", ""), cell.get("aria-label", "")]
    for element in cell.find_all(["a", "img"]):
        candidates.extend([element.get("title", ""), element.get("aria-label", ""), element.get("alt", "")])
        match = re.search(r"/player/([^/?#]+)/?", element.get("href", ""))
        if match:
            candidates.append(match.group(1).replace("-", " "))
    for candidate in candidates:
        key = norm(candidate)
        if key and len(key.split("-")) >= 2:
            return clean(candidate.replace("-", " ")), key
    return "", ""


def parse_table(table, category, roster):
    headers, rows, header_row = header_info(table)
    if not headers:
        return []
    player_column = headers.index("PLAYER")
    parsed = []
    for row in rows[header_row + 1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) <= player_column:
            continue
        player, identity = player_identity(cells[player_column])
        if not player or player.lower() in {"player", "total", "opponents", "team", "montana"}:
            continue
        if roster and identity not in roster:
            continue
        values = [clean(cell.get_text(" ", strip=True)) for cell in cells]

        def value(*names):
            index = first_index(headers, *names)
            return values[index] if index is not None and index < len(values) else ""

        if category == "passing":
            line = f'{value("CMP", "COMP") or "0"} CMP • {value("YDS") or "0"} YDS • {value("TD") or "0"} TD • {value("INT") or "0"} INT'
            extra = f'Long: {value("LONG")}' if value("LONG") else ""
        elif category == "rushing":
            line = f'{value("ATT", "CAR", "CARRIES") or "0"} CAR • {value("NET", "YDS") or "0"} YDS • {value("TD") or "0"} TD'
            extra = f'Avg: {value("AVG")}' if value("AVG") else ""
        elif category == "receiving":
            line = f'{value("REC", "RECEPTIONS", "NO") or "0"} REC • {value("YDS") or "0"} YDS • {value("TD") or "0"} TD'
            extra = f'Long: {value("LONG")}' if value("LONG") else ""
        elif category == "tackles":
            line = f'{value("TOT", "TKL", "TOTAL") or "0"} TKL • {value("SOLO") or "0"} SOLO'
            extra = f'{value("AST", "ASSIST") or "0"} AST'
        elif category == "pressure":
            line = f'{value("TFL YDS", "TFL") or "0"} TFL • {value("SACK YDS", "SACK", "SACKS") or "0"} SACK • {value("FF") or "0"} FF'
            extra = f'{value("INT") or "0"} INT • {value("PBU", "BRUP") or "0"} PBU'
        else:
            punts = value("PUNTS")
            made = value("FGM", "MADE")
            attempts = value("FGA", "ATT")
            if punts:
                line = f'{punts} PUNTS • {value("YDS") or "0"} YDS • {value("AVG") or "0"} AVG'
                extra = f'Long: {value("LONG")}' if value("LONG") else ""
            elif made or attempts:
                line, extra = f'{made or "0"}/{attempts or "0"} FG', ""
            else:
                continue
        parsed.append({"player": player, "line": line, "extra": extra})
    return parsed


def main():
    stats_response = requests.get(STATS_URL, headers=HEADERS, timeout=45)
    stats_response.raise_for_status()
    roster_response = requests.get(ROSTER_URL, headers=HEADERS, timeout=45)
    roster_response.raise_for_status()
    roster = roster_identities(BeautifulSoup(roster_response.text, "html.parser"))
    if len(roster) < 20:
        raise RuntimeError(f"Montana roster identity check failed: only {len(roster)} identities found")

    soup = BeautifulSoup(stats_response.text, "html.parser")
    data = json.loads(DATA.read_text(encoding="utf-8"))
    stats = data.setdefault("stats", {})
    existing = stats.get("leaders", {})
    leaders = {category: [] for category in CATEGORIES}

    for table in soup.find_all("table"):
        headers, _, _ = header_info(table)
        for category in categories_for(headers):
            parsed = parse_table(table, category, roster)
            if parsed and not leaders[category]:
                leaders[category] = parsed[:5]

    for category in CATEGORIES:
        if not leaders[category] and existing.get(category):
            leaders[category] = existing[category]

    if not any(leaders.values()):
        raise RuntimeError("No Montana player-stat categories were found")

    stats["leaders"] = leaders
    stats["leaders_source"] = STATS_URL
    stats["leaders_updated"] = data.get("updated")
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Montana-only player categories refreshed or safely preserved:", ", ".join(c for c in CATEGORIES if leaders[c]))


if __name__ == "__main__":
    main()
