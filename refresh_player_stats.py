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
    has = lambda *names: col(headers, *names) is not None
    if has("COMP", "CMP") and has("ATT") and has("YDS") and has("TD"):
        return "passing"
    if has("REC", "RECEPTIONS") and has("YDS") and has("TD"):
        return "receiving"
    if has("CAR", "RUSH", "ATT") and has("YDS") and has("TD"):
        return "rushing"
    if has("TOT") and has("SOLO") and has("AST"):
        return "tackles"
    if has("TFL") or has("SACK", "SACKS") or has("FF"):
        return "pressure"
    if has("PUNTS") or has("FGM") or has("XPM") or has("FGA") or has("XPA"):
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

        def parse_visible_dom():
            soup = BeautifulSoup(page.content(), "html.parser")
            found = set()
            for table in soup.find_all("table"):
                headers, _, _ = headers_and_rows(table)
                category = classify(headers)
                if category:
                    parse_table(table, category, totals)
                    found.add(category)
            return found

        # Parse the initial DOM first. Some GoGriz releases render all tables
        # in the page markup while the tab controls themselves are not visible
        # to Playwright. The old code only parsed after a successful tab click,
        # which caused every category to be reported missing.
        found_categories = parse_visible_dom()

        # Then make best-effort attempts to activate tab controls. A missing or
        # hidden tab must not prevent parsing tables that are already present.
        labels = ["Passing", "Rushing", "Receiving", "Defense", "Special Teams", "Offense"]
        for label in labels:
            try:
                locator = page.get_by_text(label, exact=True).first
                if locator.count():
                    try:
                        locator.click(timeout=2500)
                    except Exception:
                        # React/HTML tab controls may be present but hidden;
                        # dispatch a normal DOM click as a fallback.
                        locator.evaluate("el => el.click()")
                    page.wait_for_timeout(350)
                    found_categories.update(parse_visible_dom())
            except Exception as exc:
                print(f"NOTICE: could not open {label} tab: {exc}")

        print("Parsed player-stat categories: " + ", ".join(sorted(found_categories)))
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
