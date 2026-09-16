#!/usr/bin/env python3
"""Build current-season player leaders from the official GoGriz stats page."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

DATA = Path("data.json")
URL = "https://gogriz.com/sports/football/stats/2026"
CATEGORIES = ("passing", "rushing", "receiving", "tackles", "pressure", "special")
TAB_LABELS = {
    "passing": ("Passing",),
    "rushing": ("Rushing",),
    "receiving": ("Receiving",),
    "tackles": ("Defense", "Tackles"),
    "pressure": ("Defense", "Pressure"),
    "special": ("Special Teams", "Kicking", "Punting"),
}


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def num(value):
    match = re.search(r"-?\d+(?:\.\d+)?", clean(value).replace(",", ""))
    return float(match.group()) if match else 0.0


def norm(value):
    return re.sub(r"[^A-Z0-9]+", " ", clean(value).upper()).strip()


def col(headers, *names):
    wanted = {norm(x) for x in names}
    for i, header in enumerate(headers):
        h = norm(header)
        if h in wanted or any(h.startswith(x + " ") for x in wanted):
            return i
    return None


def table_info(table):
    rows = table.find_all("tr")
    for i, row in enumerate(rows[:50]):
        cells = row.find_all(["th", "td"])
        headers = [clean(c.get_text(" ", strip=True)) for c in cells]
        if any(norm(h) in {"PLAYER", "NAME", "ATHLETE", "PLAYER NAME"} for h in headers):
            return headers, rows, i
    return [], [], -1


def classify(headers, context=""):
    text = " ".join(norm(x) for x in headers) + " " + norm(context)
    has = lambda *names: col(headers, *names) is not None
    if "PRESSURE" in text or has("TFL") or has("SACK", "SACKS") or has("QH"):
        return "pressure"
    if has("SOLO") and has("AST") and has("TOT", "TOTAL"):
        return "tackles"
    if has("COMP", "CMP") and has("ATT") and has("YDS") and has("TD"):
        return "passing"
    if has("REC", "RECEPTIONS") and has("YDS") and has("TD"):
        return "receiving"
    if (has("CAR") or has("RUSH", "RUSH ATT", "RUSHING")) and has("YDS") and has("TD"):
        return "rushing"
    if has("PUNTS") or has("FGM") or has("XPM") or has("FGA") or has("XPA") or "SPECIAL" in text or "KICK" in text:
        return "special"
    return None


def player_name(cells):
    for cell in cells:
        for a in cell.find_all("a"):
            text = clean(a.get_text(" ", strip=True))
            if len(text.split()) >= 2 and text.lower() not in {"total", "opponents"}:
                return text
    for cell in cells:
        text = clean(cell.get_text(" ", strip=True))
        text = re.sub(r"^\s*#?\d+\s*", "", text)
        if not text or text.lower() in {"total", "opponents", "player", "name", "athlete"}:
            continue
        if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", text):
            continue
        if len(text.split()) >= 2 and not re.search(r"\b(?:gp|att|yds|td|int|solo|ast|tot|tfl|sack|ff)\b", text, re.I):
            return text
    return ""


def parse_table(table, category, totals):
    headers, rows, header_index = table_info(table)
    if not headers:
        return
    for row in rows[header_index + 1:]:
        cells = row.find_all(["td", "th"])
        name = player_name(cells)
        if not name or name.lower() in {"total", "opponents"}:
            continue
        values = [clean(c.get_text(" ", strip=True)) for c in cells]

        def value(*names):
            i = col(headers, *names)
            return num(values[i]) if i is not None and i < len(values) else 0.0

        if category == "passing":
            metrics = {"cmp": value("COMP", "CMP"), "yds": value("YDS"), "td": value("TD"), "int": value("INT")}
        elif category == "rushing":
            metrics = {"att": value("CAR", "RUSH", "RUSH ATT", "ATT"), "yds": value("YDS"), "td": value("TD")}
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


def collect(page, totals):
    soup = BeautifulSoup(page.content(), "html.parser")
    for table in soup.find_all("table"):
        headers, _, _ = table_info(table)
        if not headers:
            continue
        heading = table.find_previous(["h1", "h2", "h3", "h4", "caption"])
        context = heading.get_text(" ", strip=True) if heading else ""
        category = classify(headers, context)
        if category:
            parse_table(table, category, totals)


def click_exact(page, label):
    loc = page.get_by_text(label, exact=True)
    clicked = False
    for i in range(min(loc.count(), 8)):
        try:
            loc.nth(i).click(timeout=5000, force=True)
            page.wait_for_timeout(1200)
            clicked = True
        except Exception:
            pass
    return clicked


def parse_rendered_page():
    totals = {c: defaultdict(lambda: defaultdict(float)) for c in CATEGORIES}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1800})
        try:
            # GoGriz keeps background requests open, so networkidle can time out
            # even after the stats page is fully usable. DOMContentLoaded is the
            # correct readiness point; the explicit wait below handles rendering.
            try:
                page.goto(URL, wait_until="domcontentloaded", timeout=90000)
            except PlaywrightTimeoutError:
                print("Warning: GoGriz navigation timed out; using the rendered page that is available.")
            page.wait_for_timeout(6000)
            collect(page, totals)
            for category in CATEGORIES:
                for label in TAB_LABELS[category]:
                    click_exact(page, label)
                    collect(page, totals)
        finally:
            browser.close()
    return totals


def build_leaders(totals):
    result = {c: [] for c in CATEGORIES}
    keys = {"passing": "yds", "rushing": "yds", "receiving": "yds", "tackles": "tot", "pressure": "tfl", "special": "made"}
    for category in CATEGORIES:
        rows = sorted(totals[category].values(), key=lambda r: (-r[keys[category]], r["player"]))
        for row in [r for r in rows if r[keys[category]] > 0][:5]:
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
    leaders = build_leaders(parse_rendered_page())
    missing = [c for c in CATEGORIES if not leaders[c]]
    if missing:
        raise RuntimeError("Official 2026 player tables were not parsed completely; missing: " + ", ".join(missing))
    stats["leaders"] = leaders
    stats["leaders_source"] = URL
    stats["leaders_checked_at"] = datetime.now(timezone.utc).isoformat()
    stats.pop("leaders_preserved_categories", None)
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Published official 2026 season player leaders: " + ", ".join(f"{k}={len(v)}" for k, v in leaders.items()))


if __name__ == "__main__":
    main()
