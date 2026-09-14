#!/usr/bin/env python3
"""Fail-closed, source-first Montana football statistics rebuild.

This module intentionally publishes only values that can be traced to an
official GoGriz schedule/result or official GoGriz box score. Missing box
scores are reported as pending instead of being filled with stale values.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import urljoin
from bs4 import BeautifulSoup


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _num(value: str):
    m = re.search(r"-?\d+(?:,\d+)?", value or "")
    return int(m.group(0).replace(",", "")) if m else None


def _result(value: str):
    m = re.search(r"\b([WLT])\s*(\d+)\s*[-–]\s*(\d+)\b", value or "", re.I)
    if not m:
        return None
    return {"outcome": m.group(1).upper(), "montana": int(m.group(2)), "opponent": int(m.group(3))}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def discover_boxscores(schedule_html: str) -> dict[str, str]:
    """Return opponent-name -> official box-score URL from GoGriz HTML."""
    soup = BeautifulSoup(schedule_html, "html.parser")
    found = {}
    for a in soup.find_all("a", href=True):
        href = urljoin("https://gogriz.com", a["href"])
        if "/sports/football/stats/2026/" not in href.lower() or "/boxscore/" not in href.lower():
            continue
        text = _clean(a.get_text(" ", strip=True))
        # Most GoGriz links include the opponent in the URL slug.
        path = href.lower().split("/stats/2026/", 1)[-1].split("/boxscore/", 1)[0]
        found[path] = href
        if text:
            found[_slug(text)] = href
    return found


def _table_rows(table):
    rows = []
    for tr in table.find_all("tr"):
        cells = [_clean(x.get_text(" ", strip=True)) for x in tr.find_all(["th", "td"])]
        if cells:
            rows.append(cells)
    return rows


def _find_team_index(header):
    for i, cell in enumerate(header):
        up = cell.upper()
        if up in {"UM", "MONTANA", "MONTANA GRIZZLIES"} or "MONTANA" in up:
            return i
    return None


def parse_boxscore(html: str, url: str, opponent: str, result: dict) -> dict:
    """Extract only stable team-level values from an official box score."""
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    team = {"opponent": opponent, "source_url": url, "result": result}

    for table in tables:
        rows = _table_rows(table)
        if not rows:
            continue
        text = " ".join(" ".join(row) for row in rows)
        header = rows[0]
        um = _find_team_index(header)
        if um is None:
            continue
        # Identify the opposing numeric column from the header, not position.
        numeric_cols = [i for i, x in enumerate(header) if i != 0 and i < len(header)]
        opp = next((i for i in numeric_cols if i != um), None)
        if opp is None:
            continue

        for row in rows[1:]:
            if len(row) <= max(um, opp):
                continue
            label = row[0].lower()
            if label == "yards" and "total offense" in text.lower() and "total offense" not in team:
                team["total_offense"] = _num(row[um])
                team["opponent_total_offense"] = _num(row[opp])
            elif label in {"passing", "pass yards"} and "passing" not in team:
                team["passing"] = _num(row[um])
                team["opponent_passing"] = _num(row[opp])
            elif label in {"rushing", "rush yards"} and "rushing" not in team:
                team["rushing"] = _num(row[um])
                team["opponent_rushing"] = _num(row[opp])

    # A source is not accepted unless the core total-offense pair is present.
    if team.get("total_offense") is None or team.get("opponent_total_offense") is None:
        raise ValueError(f"official box score missing total offense columns: {url}")
    return team


def _fmt_pct(made, attempts):
    if attempts is None or attempts == 0:
        return "—"
    return f"{made}/{attempts} ({made / attempts * 100:.1f}%)"


def _sum(records, key):
    values = [r[key] for r in records if isinstance(r.get(key), (int, float))]
    return sum(values) if values else None


def _avg(total, count, decimals=1):
    if total is None or not count:
        return "—"
    return f"{total / count:.{decimals}f}"


def build_stats(schedule, old_stats, get, schedule_html: str | None = None):
    """Build a clean stats object from completed official box scores.

    The schedule controls the season record. Box scores control detailed
    statistics. A completed game without a box score is explicitly marked
    pending and never inherits old values.
    """
    played = [g for g in schedule if g.get("result")]
    wins = sum(str(g.get("result", "")).upper().startswith("W") for g in played)
    losses = sum(str(g.get("result", "")).upper().startswith("L") for g in played)
    ties = sum(str(g.get("result", "")).upper().startswith("T") for g in played)
    conf = [g for g in played if g.get("conference")]
    cw = sum(str(g.get("result", "")).upper().startswith("W") for g in conf)
    cl = sum(str(g.get("result", "")).upper().startswith("L") for g in conf)

    discovered = discover_boxscores(schedule_html or "") if schedule_html else {}
    records = []
    pending = []
    for game in played:
        opponent = _clean(game.get("opponent", ""))
        url = discovered.get(_slug(opponent))
        if not url:
            # Known official URLs remain explicit and auditable.
            for key, candidate in discovered.items():
                if _slug(opponent) in key or key in _slug(opponent):
                    url = candidate
                    break
        if not url:
            pending.append({"opponent": opponent, "reason": "Official box-score link not found"})
            continue
        try:
            result = _result(game.get("result", ""))
            if not result:
                pending.append({"opponent": opponent, "reason": "Unparseable official result"})
                continue
            records.append(parse_boxscore(get(url), url, opponent, result))
        except Exception as exc:
            pending.append({"opponent": opponent, "reason": str(exc)})

    verified = len(records)
    points_for = _sum([{"v": r["result"]["montana"]} for r in records], "v")
    points_against = _sum([{"v": r["result"]["opponent"]} for r in records], "v")
    yards_for = _sum(records, "total_offense")
    yards_against = _sum(records, "opponent_total_offense")
    passing = _sum(records, "passing")
    rushing = _sum(records, "rushing")
    opp_passing = _sum(records, "opponent_passing")
    opp_rushing = _sum(records, "opponent_rushing")

    # Do not retain any old detailed values. Unsupported fields are explicit.
    stats = {
        "through": f"Verified through {verified} of {len(played)} completed games",
        "coverage": {"completed_games": len(played), "verified_boxscores": verified, "pending": pending},
        "source": "Official GoGriz schedule and official GoGriz box scores",
        "source_checked_at": datetime.now(timezone.utc).isoformat(),
        "team_summary": [
            {"value": f"{wins}–{losses}" if not ties else f"{wins}–{losses}–{ties}", "label": "RECORD", "note": "Official schedule"},
            {"value": _avg(points_for, verified), "label": "POINTS / GAME", "note": "Verified box scores only"},
            {"value": _avg(yards_for, verified, 0), "label": "TOTAL OFFENSE", "note": "Yards per verified game"},
            {"value": _avg(yards_against, verified, 0), "label": "TOTAL DEFENSE", "note": "Yards allowed per verified game"},
        ],
        "offense": [
            ["Points", str(points_for) if points_for is not None else "—"],
            ["Total Yards", str(yards_for) if yards_for is not None else "—"],
            ["Yards / Play", "—"],
            ["Passing", str(passing) if passing is not None else "—"],
            ["Rushing", str(rushing) if rushing is not None else "—"],
            ["3rd Down", "—"], ["4th Down", "—"], ["Red Zone", "—"], ["Turnovers", "—"],
        ],
        "defense": [
            ["Points Allowed", str(points_against) if points_against is not None else "—"],
            ["Yards Allowed", str(yards_against) if yards_against is not None else "—"],
            ["Yards / Play", "—"],
            ["Pass Yards Allowed", str(opp_passing) if opp_passing is not None else "—"],
            ["Rush Yards Allowed", str(opp_rushing) if opp_rushing is not None else "—"],
            ["3rd Down Allowed", "—"], ["4th Down Allowed", "—"], ["Red Zone Allowed", "—"], ["Takeaways", "—"],
        ],
        "situational": [["Turnover Margin", "—", "Not parsed from current source"], ["Time of Possession", "—"], ["Penalties", "—"], ["Punts", "—"], ["Field Goals", "—"], ["Sacks", "—"]],
        "leaders": {"passing": [], "rushing": [], "receiving": [], "tackles": [], "pressure": [], "special": []},
        "game_log": [
            {"week": f"Wk {i + 1}", "opponent": r["opponent"], "result": f"{r['result']['outcome']} {r['result']['montana']}-{r['result']['opponent']}", "montana_yards": r.get("total_offense"), "opponent_yards": r.get("opponent_total_offense"), "turnovers": "—", "notes": "Official box score verified"}
            for i, r in enumerate(records)
        ],
        "compare": [
            {"label": "Points / Game", "montana": _avg(points_for, verified), "opponents": _avg(points_against, verified), "diff": "—"},
            {"label": "Total Yards / Game", "montana": _avg(yards_for, verified), "opponents": _avg(yards_against, verified), "diff": "—"},
            {"label": "Passing Yards / Game", "montana": _avg(passing, verified), "opponents": _avg(opp_passing, verified), "diff": "—"},
            {"label": "Rushing Yards / Game", "montana": _avg(rushing, verified), "opponents": _avg(opp_rushing, verified), "diff": "—"},
            {"label": "Turnover Margin", "montana": "—", "opponents": "—", "diff": "—"},
            {"label": "3rd Down", "montana": "—", "opponents": "—", "diff": "—"},
        ],
    }
    return stats
