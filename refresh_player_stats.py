#!/usr/bin/env python3
"""Build player leaders from the rendered official GoGriz statistics page."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

DATA = Path("data.json")
URL = "https://gogriz.com/sports/football/stats/2026"
CATEGORIES = ("passing", "rushing", "receiving", "tackles", "pressure", "special")


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def num(value):
    match = re.search(r"-?\d+(?:\.\d+)?", clean(value).replace(",", ""))
    return float(match.group()) if match else 0.0


def headers_and_rows(table):
    rows = table.find_all("tr")
    for i, row in enumerate(rows[:25]):
        headers = [clean(c.get_text(" ", strip=True)).upper() for c in row.find_all(["th", "td"])]
        if "PLAYER" in headers:
            return headers, rows, i
    return [], [], -1


def col(headers, *names):
    for name in names:
        for i, header in enumerate(headers):
            if header == name or header.startswith(name + " "):
                return i
    return None


def classify(headers):
    # Normalize punctuation/spacing because GoGriz has used several header
    # spellings (ATT, CAR, RUSH; CMP, COMP; RECEPTIONS, REC).
    normalized = {re.sub(r"[^A-Z0-9]", "", h.upper()) for h in headers}
    has = lambda *names: any(re.sub(r"[^A-Z0-9]", "", n.upper()) in normalized for n in names)
    if has("COMP", "CMP", "COMPLETIONS") and has("ATT", "ATTEMPTS") and has("YDS", "YARDS") and has("TD", "TOUCHDOWNS"):
        return "passing"
    if has("REC", "RECEPTIONS") and has("YDS", "YARDS") and has("TD", "TOUCHDOWNS"):
        return "receiving"
    if has("CAR", "RUSH", "RUSHATT", "ATT") and has("YDS", "YARDS") and has("TD", "TOUCHDOWNS"):
        return "rushing"
    if has("TOT", "TOTAL", "TACKLES") and has("SOLO") and has("AST", "ASSIST"):
        return "tackles"
    if has("TFL", "TACKLESFORLOSS") or has("SACK", "SACKS") or has("FF", "FUMBLESFORCED"):
        return "pressure"
    if has("PUNTS", "PUNT") or has("FGM", "XPM", "MADE") or has("FGA", "XPA", "ATTEMPTS"):
        return "special"
    return None


def player_name(cells):
    # GoGriz places the real player name in an anchor; do not depend on the
    # visual text extraction of the first/# column.
    for cell in cells:
        for anchor in cell.find_all("a"):
            text = clean(anchor.get_text(" ", strip=True))
            if len(text.split()) >= 2 and text.lower() not in {"total", "opponents"}:
                return text
    for cell in cells:
        text = clean(cell.get_text(" ", strip=True))
        text = re.sub(r"^\d+\s+", "", text)
        if len(text.split()) >= 2 and text.lower() not in {"total", "opponents"}:
            return text
    return ""


def parse_table(table, category, totals):
    headers, rows, header_index = headers_and_rows(table)
    if not headers:
        return
    player_index = col(headers, "PLAYER")
    if player_index is None:
        return
    for row in rows[header_index + 1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) <= player_index:
            continue
        name = player_name(cells)
        if not name:
            continue
        values = [clean(c.get_text(" ", strip=True)) for c in cells]

        def value(*names):
            index = col(headers, *names)
            return num(values[index]) if index is not None and index < len(values) else 0.0

        if category == "passing":
            metrics = {"cmp": value("COMP", "CMP"), "yds": value("YDS"), "td": value("TD"), "int": value("INT")}
        elif category == "rushing":
            metrics = {"att": value("CAR", "RUSH", "ATT"), "yds": value("YDS"), "td": value("TD")}
        elif category == "receiving":
            metrics = {"rec": value("REC", "RECEPTIONS"), "yds": value("YDS"), "td": value("TD")}
        elif category == "tackles":
            metrics = {"tot": value("TOT"), "solo": value("SOLO"), "ast": value("AST")}
        elif category == "pressure":
            metrics = {"tfl": value("TFL"), "sacks": value("SACK", "SACKS"), "ff": value("FF"), "int": value("INT")}
        else:
            metrics = {"made": value("FGM", "XPM"), "attempts": value("FGA", "XPA"), "punts": value("PUNTS"), "yds": value("YDS")}

        bucket = totals[category][name]
        bucket["player"] = name
        for key, amount in metrics.items():
            bucket[key] += amount


def parse_rendered_page():
    totals = {category: defaultdict(lambda: defaultdict(float)) for category in CATEGORIES}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1200})
        page.goto(URL, wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(1500)

        # Parse any tables already present, then attempt every known tab.
        # GoGriz has changed the tab markup several times, so use buttons/tabs/
        # links and a DOM-click fallback rather than one exact text locator.
        def parse_visible_tables():
            soup = BeautifulSoup(page.content(), "html.parser")
            for table in soup.find_all("table"):
                headers, _, _ = headers_and_rows(table)
                category = classify(headers)
                if category:
                    parse_table(table, category, totals)

        parse_visible_tables()
        labels = ["Passing", "Rushing", "Receiving", "Defense", "Special Teams", "Offense", "Kicking", "Punting"]
        for label in labels:
            try:
                candidates = page.locator("button, [role='tab'], a").filter(has_text=label)
                if candidates.count():
                    target = candidates.first
                    try:
                        target.click(timeout=3000, force=True)
                    except Exception:
                        target.evaluate("el => el.click()")
                    page.wait_for_timeout(700)
                    parse_visible_tables()
            except Exception as exc:
                print(f"NOTICE: could not open {label} tab: {exc}")
        browser.close()
    return totals


def build_leaders(totals):
    result = {category: [] for category in CATEGORIES}
    sort_key = {"passing": "yds", "rushing": "yds", "receiving": "yds", "tackles": "tot", "pressure": "tfl", "special": "made"}
    for category in CATEGORIES:
        rows = sorted(totals[category].values(), key=lambda r: (-r[sort_key[category]], r["player"]))
        for row in [r for r in rows if r[sort_key[category]] > 0][:5]:
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
    leaders = build_leaders(parse_rendered_page())
    missing = [category for category in CATEGORIES if not leaders[category]]
    if missing:
        raise RuntimeError("Rendered GoGriz player tables were only partially parsed; missing: " + ", ".join(missing))
    data = json.loads(DATA.read_text(encoding="utf-8"))
    stats = data.setdefault("stats", {})
    stats["leaders"] = leaders
    stats["leaders_source"] = URL
    stats["leaders_checked_at"] = datetime.now(timezone.utc).isoformat()
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Published complete official player leaders: " + ", ".join(f"{k}={len(v)}" for k, v in leaders.items()))


if __name__ == "__main__":
    main()
