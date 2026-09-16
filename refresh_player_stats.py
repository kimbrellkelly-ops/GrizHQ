#!/usr/bin/env python3
"""Build current-season player leaders from the official GoGriz stats page."""
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
    for i, row in enumerate(rows[:30]):
        headers = [clean(c.get_text(" ", strip=True)).upper() for c in row.find_all(["th", "td"])]
        if "PLAYER" in headers:
            return headers, rows, i
    return [], [], -1


def col(headers, *names):
    normalized = [re.sub(r"[^A-Z0-9]+", " ", h).strip() for h in headers]
    for name in names:
        wanted = re.sub(r"[^A-Z0-9]+", " ", name.upper()).strip()
        for i, header in enumerate(normalized):
            if header == wanted or header.startswith(wanted + " "):
                return i
    return None


def classify(headers):
    has = lambda *names: col(headers, *names) is not None
    if has("TFL") or has("SACK", "SACKS") or has("FF") or has("QH"):
        return "pressure"
    if has("SOLO") and has("AST") and has("TOT", "TOTAL"):
        return "tackles"
    if has("COMP", "CMP") and has("ATT") and has("YDS") and has("TD"):
        return "passing"
    if has("REC", "RECEPTIONS") and has("YDS") and has("TD"):
        return "receiving"
    if has("CAR", "RUSH", "ATT") and has("YDS") and has("TD"):
        return "rushing"
    if has("PUNTS") or has("FGM") or has("XPM") or has("FGA") or has("XPA") or has("KICK"):
        return "special"
    return None


def player_name(cells):
    for cell in cells:
        for anchor in cell.find_all("a"):
            text = clean(anchor.get_text(" ", strip=True))
            if len(text.split()) >= 2 and text.lower() not in {"total", "opponents"}:
                return text
    for cell in cells:
        text = re.sub(r"^\d+\s+", "", clean(cell.get_text(" ", strip=True)))
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
            metrics = {"tot": value("TOT", "TOTAL"), "solo": value("SOLO"), "ast": value("AST")}
        elif category == "pressure":
            metrics = {"tfl": value("TFL"), "sacks": value("SACK", "SACKS"), "ff": value("FF"), "int": value("INT")}
        else:
            metrics = {"made": value("FGM", "XPM"), "attempts": value("FGA", "XPA"), "punts": value("PUNTS"), "yds": value("YDS")}

        bucket = totals[category][name]
        bucket["player"] = name
        for key, amount in metrics.items():
            bucket[key] += amount


def collect_tables(page, totals):
    soup = BeautifulSoup(page.content(), "html.parser")
    for table in soup.find_all("table"):
        headers, _, _ = headers_and_rows(table)
        category = classify(headers)
        if category:
            parse_table(table, category, totals)


def parse_rendered_page():
    totals = {category: defaultdict(lambda: defaultdict(float)) for category in CATEGORIES}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1600})
        page.goto(URL, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(2500)
        collect_tables(page, totals)

        wanted = {"passing", "rushing", "receiving", "defense", "special teams", "offense", "special", "kicking", "punting"}
        controls = page.locator("button, a, [role='tab'], [role='button']")
        for i in range(controls.count()):
            control = controls.nth(i)
            try:
                label = clean(control.inner_text()).lower()
            except Exception:
                continue
            if label not in wanted:
                continue
            try:
                control.click(timeout=2500, force=True)
            except Exception:
                try:
                    control.evaluate("el => el.click()")
                except Exception:
                    continue
            page.wait_for_timeout(700)
            collect_tables(page, totals)

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
    data = json.loads(DATA.read_text(encoding="utf-8"))
    stats = data.setdefault("stats", {})
    previous = stats.get("leaders", {}) if isinstance(stats.get("leaders", {}), dict) else {}
    leaders = build_leaders(parse_rendered_page())

    # The GoGriz page can expose only some category tabs to headless browsers.
    # Never fail the entire data refresh or erase a previously published category
    # just because one rendered tab was unavailable on this run.
    preserved = []
    for category in CATEGORIES:
        if not leaders[category] and isinstance(previous.get(category), list) and previous[category]:
            leaders[category] = previous[category]
            preserved.append(category)

    data_missing = [category for category in CATEGORIES if not leaders[category]]
    if data_missing:
        raise RuntimeError("No player leaders available for: " + ", ".join(data_missing))

    stats["leaders"] = leaders
    stats["leaders_source"] = URL
    stats["leaders_checked_at"] = datetime.now(timezone.utc).isoformat()
    stats["leaders_preserved_categories"] = preserved
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    message = "Published official player leaders: " + ", ".join(f"{k}={len(v)}" for k, v in leaders.items())
    if preserved:
        message += "; preserved unavailable categories: " + ", ".join(preserved)
    print(message)


if __name__ == "__main__":
    main()
