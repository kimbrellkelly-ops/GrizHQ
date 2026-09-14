#!/usr/bin/env python3
"""Rebuild Montana player leaders from the official GoGriz cumulative tables.

This file deliberately replaces the complete leaders object on every run. It never
merges or preserves stale player leaders from data.json.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA = Path("data.json")
URL = "https://gogriz.com/sports/football/stats/2026"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GrizHQ/1.0)"}
CATEGORIES = ("passing", "rushing", "receiving", "tackles", "pressure", "special")


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def number(value):
    match = re.search(r"-?\d+(?:\.\d+)?", clean(value).replace(",", ""))
    return float(match.group()) if match else 0.0


def soup(url):
    response = requests.get(url, headers=HEADERS, timeout=45)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def table_header(table):
    rows = table.find_all("tr")
    for index, row in enumerate(rows[:20]):
        cells = row.find_all(["th", "td"])
        values = [clean(c.get_text(" ", strip=True)).upper() for c in cells]
        if any(v == "PLAYER" or v.startswith("PLAYER ") for v in values):
            return values, rows, index
    return [], [], -1


def column(headers, *wanted):
    for wanted_name in wanted:
        for index, value in enumerate(headers):
            if value == wanted_name or value.startswith(wanted_name + " "):
                return index
    return None


def classify(headers):
    has = lambda *names: column(headers, *names) is not None
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


def player_name(cell):
    """Extract the visible player name without requiring a separate roster lookup."""
    candidates = []
    for node in [cell] + cell.find_all(["a", "span"]):
        for attr in ("data-name", "aria-label", "title"):
            value = clean(node.get(attr, ""))
            if value:
                candidates.append(value)
        value = clean(node.get_text(" ", strip=True))
        if value:
            candidates.append(value)
    for value in candidates:
        value = re.sub(r"^\d+\s+", "", value)
        value = re.sub(r"\b(?:QB|RB|WR|TE|OL|DL|LB|DB|S|CB|FB|K|P|LS)\b", " ", value, flags=re.I)
        value = clean(value)
        if len(value.split()) >= 2 and not value.lower().startswith(("total", "opponents")):
            return value
    return ""


def parse_table(table, category, totals):
    headers, rows, header_index = table_header(table)
    if not headers:
        return
    player_col = column(headers, "PLAYER")
    if player_col is None:
        return
    for row in rows[header_index + 1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) <= player_col:
            continue
        name = player_name(cells[player_col])
        if not name:
            continue
        values = [clean(cell.get_text(" ", strip=True)) for cell in cells]

        def v(*names):
            index = column(headers, *names)
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

        bucket = totals[category][name]
        bucket["player"] = name
        for metric, amount in metrics.items():
            bucket[metric] += amount


def output(totals):
    result = {category: [] for category in CATEGORIES}
    sort_metric = {"passing": "yds", "rushing": "yds", "receiving": "yds", "tackles": "tot", "pressure": "tfl", "special": "made"}
    for category in CATEGORIES:
        rows = sorted(totals[category].values(), key=lambda row: (-row[sort_metric[category]], row["player"]))
        for row in [row for row in rows if row[sort_metric[category]] > 0][:5]:
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
            result[category].append({"player": row["player"], "line": line, "extra": extra})
    return result


def main():
    page = soup(URL)
    totals = {category: defaultdict(lambda: defaultdict(float)) for category in CATEGORIES}
    for table in page.find_all("table"):
        headers, _, _ = table_header(table)
        category = classify(headers)
        if category:
            parse_table(table, category, totals)

    leaders = output(totals)
    if not any(leaders.values()):
        raise RuntimeError("Official GoGriz page produced no player leaders; refusing to overwrite data.json")

    data = json.loads(DATA.read_text(encoding="utf-8"))
    stats = data.setdefault("stats", {})
    stats["leaders"] = leaders
    stats["leaders_source"] = URL
    stats["leaders_checked_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    counts = ", ".join(f"{key}={len(value)}" for key, value in leaders.items())
    print(f"Published fresh official player leaders: {counts}")


if __name__ == "__main__":
    main()
