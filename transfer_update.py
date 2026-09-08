#!/usr/bin/env python3
"""Refresh the Griz HQ transfer tracker from official destination-school stats.

Safety rules:
- Only update the existing Griz Transfers section in index.html.
- Never erase a previously published stat when a source is unavailable.
- Never invent a 2026 stat. A player changes only when an official stats page
  returns a matching player row.
- Source failures are warnings, not workflow failures.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
import sys
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
TIMEOUT = 25
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; GrizHQ transfer tracker/1.0; +https://gogriz.com/)"
}

PLAYERS = [
    {"name": "Malae Fonoti", "source": "https://mutigers.com/sports/football/stats", "kind": "offense"},
    {"name": "Colin Amick", "source": "https://cyclones.com/sports/football/stats/2026", "kind": "offense"},
    {"name": "Jose Balver-Mendoza", "source": "https://nevadawolfpack.com/sports/football/stats/2026", "kind": "offense"},
    {"name": "Jareb Ramos", "source": "https://cyclones.com/sports/football/stats/2026", "kind": "defense"},
    {"name": "Caleb Otlewski", "source": "https://csurams.com/sports/football/stats/2026", "kind": "defense"},
    {"name": "Diezel Wilkinson", "source": "https://uabsports.com/sports/football/stats/2026", "kind": "defense"},
    {"name": "Kyon Loud", "source": "https://goduke.com/sports/football/stats/2026", "kind": "defense"},
    {"name": "Rashid Mansour", "source": "https://hcuhuskies.com/sports/football/stats/2026", "kind": "defense"},
    {"name": "Terahiti Wolfe", "source": "https://goviks.com/sports/football/stats/?path=football", "kind": "defense"},
    {"name": "Justus Breston", "source": "https://goumary.com/sports/football/stats/2026", "kind": "defense"},
    {"name": "Micah Harper", "source": "https://cyclones.com/sports/football/stats/2026", "kind": "defense"},
]


def norm(text: str) -> str:
    text = text.lower().replace("’", "'")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def player_matches(cell_text: str, full_name: str) -> bool:
    text = norm(cell_text)
    first, last = norm(full_name).split(" ", 1)
    variants = {
        norm(full_name),
        norm(f"{last}, {first}"),
        norm(f"{last} {first}"),
    }
    return any(v == text or v in text for v in variants)


def numeric(value: str):
    value = value.strip()
    if not value or value in {"--", "—", "-"}:
        return None
    # Handle values such as 4.0 or 2.5-17 while preserving the first number.
    m = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
    if not m:
        return None
    n = float(m.group())
    return int(n) if n.is_integer() else n


def fetch_player_stats(url: str, player: str) -> dict | None:
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    found = {"gp": None, "starts": None, "snaps": None, "rush_att": None,
             "rush_yds": None, "rush_td": None, "rec": None, "rec_yds": None,
             "rec_td": None, "tackles": None, "tfl": None, "sacks": None,
             "ints": None, "pbu": None}
    matched = False

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        header_idx = None
        headers = []
        for i, row in enumerate(rows[:6]):
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
            normalized = [norm(c) for c in cells]
            if any(c == "player" or c.startswith("player ") for c in normalized):
                header_idx = i
                headers = cells
                break
        if header_idx is None:
            continue
        header_norm = [norm(h) for h in headers]
        player_idx = next((i for i, h in enumerate(header_norm) if h == "player" or h.startswith("player ")), None)
        if player_idx is None:
            continue

        for row in rows[header_idx + 1:]:
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
            if len(cells) != len(headers):
                continue
            if not player_matches(cells[player_idx], player):
                continue
            matched = True
            values = dict(zip(header_norm, cells))

            def pick(*keys):
                for key in keys:
                    if key in values:
                        return numeric(values[key])
                return None

            found["gp"] = found["gp"] or pick("gp", "games played gp")
            found["starts"] = found["starts"] or pick("gs", "starts")
            found["snaps"] = found["snaps"] or pick("snaps", "plays")

            # Rushing tables.
            if "att" in values and ("gain" in values or "net" in values) and "td" in values:
                found["rush_att"] = pick("att") if found["rush_att"] is None else max(found["rush_att"], pick("att") or 0)
                found["rush_yds"] = pick("net", "gain") if found["rush_yds"] is None else max(found["rush_yds"], pick("net", "gain") or 0)
                found["rush_td"] = pick("td") if found["rush_td"] is None else max(found["rush_td"], pick("td") or 0)

            # Receiving tables.
            if ("no" in values or "rec" in values) and "yds" in values and "td" in values:
                found["rec"] = pick("no", "rec") if found["rec"] is None else max(found["rec"], pick("no", "rec") or 0)
                found["rec_yds"] = pick("yds") if found["rec_yds"] is None else max(found["rec_yds"], pick("yds") or 0)
                found["rec_td"] = pick("td") if found["rec_td"] is None else max(found["rec_td"], pick("td") or 0)

            # Defensive tables.
            if "solo" in values and "tot" in values:
                found["tackles"] = pick("tot") if found["tackles"] is None else max(found["tackles"], pick("tot") or 0)
                tfl_raw = values.get("tfl yds", values.get("tfl", ""))
                sack_raw = values.get("sacks yds", values.get("sacks", ""))
                found["tfl"] = numeric(tfl_raw) if found["tfl"] is None else max(found["tfl"], numeric(tfl_raw) or 0)
                found["sacks"] = numeric(sack_raw) if found["sacks"] is None else max(found["sacks"], numeric(sack_raw) or 0)
                found["ints"] = pick("int") if found["ints"] is None else max(found["ints"], pick("int") or 0)
                found["pbu"] = pick("bu", "pbu", "pass brup") if found["pbu"] is None else max(found["pbu"], pick("bu", "pbu", "pass brup") or 0)

    return found if matched else None


def fmt_num(value):
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def build_line(stats: dict, kind: str) -> str:
    parts = []
    if stats.get("gp") is not None:
        parts.append(f"{fmt_num(stats['gp'])} G")
    if stats.get("starts") is not None:
        parts.append(f"{fmt_num(stats['starts'])} starts")
    if stats.get("snaps") is not None:
        parts.append(f"{fmt_num(stats['snaps'])} snaps")

    if kind == "offense":
        if stats.get("rush_att") is not None:
            parts.append(f"{fmt_num(stats['rush_att'])} rush")
            if stats.get("rush_yds") is not None:
                parts.append(f"{fmt_num(stats['rush_yds'])} yds")
            if stats.get("rush_td") is not None:
                parts.append(f"{fmt_num(stats['rush_td'])} TD")
        if stats.get("rec") is not None:
            parts.append(f"{fmt_num(stats['rec'])} rec")
            if stats.get("rec_yds") is not None:
                parts.append(f"{fmt_num(stats['rec_yds'])} rec yds")
            if stats.get("rec_td") is not None:
                parts.append(f"{fmt_num(stats['rec_td'])} rec TD")
    else:
        if stats.get("tackles") is not None:
            parts.append(f"{fmt_num(stats['tackles'])} tackles")
        if stats.get("tfl") is not None:
            parts.append(f"{fmt_num(stats['tfl'])} TFL")
        if stats.get("sacks") is not None:
            parts.append(f"{fmt_num(stats['sacks'])} sacks")
        if stats.get("ints") is not None:
            parts.append(f"{fmt_num(stats['ints'])} INT")
        if stats.get("pbu") is not None:
            parts.append(f"{fmt_num(stats['pbu'])} PBU")

    return " · ".join(parts) if parts else "No player stats posted"


def status_for(stats: dict, kind: str) -> tuple[str, str]:
    gp = stats.get("gp") or 0
    if not gp:
        return "status-white", "⚪ LIMITED ROLE"
    if kind == "offense":
        yards = (stats.get("rush_yds") or 0) + (stats.get("rec_yds") or 0)
        td = (stats.get("rush_td") or 0) + (stats.get("rec_td") or 0)
        if yards >= 100 or td >= 2:
            return "status-green", "🟢 THRIVING"
        if yards > 0 or td > 0:
            return "status-yellow", "🟡 CONTRIBUTING"
    else:
        tackles = stats.get("tackles") or 0
        sacks = stats.get("sacks") or 0
        ints = stats.get("ints") or 0
        pbu = stats.get("pbu") or 0
        if tackles >= 10 or sacks >= 2 or ints >= 2 or (ints >= 1 and pbu >= 4):
            return "status-green", "🟢 THRIVING"
        if tackles > 0 or sacks > 0 or ints > 0 or pbu > 0:
            return "status-yellow", "🟡 CONTRIBUTING"
    return "status-white", "⚪ LIMITED ROLE"


def update_index(results: dict[str, tuple[dict, str]]) -> bool:
    text = INDEX.read_text(encoding="utf-8")
    start_marker = "<!-- GRIZ TRANSFERS START -->"
    end_marker = "<!-- GRIZ TRANSFERS END -->"
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker)) if start >= 0 else -1
    if start < 0 or end < 0:
        raise RuntimeError("Griz Transfers markers not found; refusing to modify index.html")

    section = text[start + len(start_marker):end]
    soup = BeautifulSoup(section, "html.parser")
    root = soup.select_one(".griz-transfers")
    if root is None:
        raise RuntimeError("Griz Transfers section not found inside markers; refusing to modify index.html")

    changed = False
    for card in root.select(".griz-transfer-card"):
        title = card.find("h4")
        if not title:
            continue
        name = title.get_text(" ", strip=True)
        if name not in results:
            continue
        stats, kind = results[name]
        line = card.select_one(".griz-transfer-line.current span")
        if not line:
            continue
        new_line = build_line(stats, kind)
        if line.get_text(" ", strip=True) != new_line:
            line.string = new_line
            changed = True
        new_class, new_status = status_for(stats, kind)
        classes = [c for c in card.get("class", []) if not c.startswith("status-")]
        classes.append(new_class)
        if card.get("class") != classes:
            card["class"] = classes
            changed = True
        status = card.select_one(".griz-transfer-status")
        if status and status.get_text(" ", strip=True) != new_status:
            status.string = new_status
            changed = True

    # Keep the summary truthful if the tracked list changes later.
    cards = root.select(".griz-transfer-card")
    summary = root.select_one(".griz-transfer-summary")
    if summary:
        cells = summary.find_all("div", recursive=False)
        if len(cells) >= 2 and cells[0].find("b"):
            v = str(len(cards))
            if cells[0].find("b").get_text(strip=True) != v:
                cells[0].find("b").string = v
                changed = True
        if len(cells) >= 2 and cells[1].find("b"):
            # Six current FBS destinations are tracked in this version.
            fbs = {"Missouri", "Iowa State", "Nevada", "Colorado State", "UAB", "Duke"}
            destinations = set()
            for card in cards:
                dest = card.select_one(".griz-transfer-dest")
                if dest:
                    destinations.add(dest.get_text(" ", strip=True).split(" · ")[0])
            value = str(len(destinations & fbs))
            if cells[1].find("b").get_text(strip=True) != value:
                cells[1].find("b").string = value
                changed = True

    if changed:
        new_section = str(root)
        text = text[:start + len(start_marker)] + "\n" + new_section + "\n" + text[end:]
        INDEX.write_text(text, encoding="utf-8")
    return changed


def main() -> int:
    results = {}
    successes = 0
    for player in PLAYERS:
        name = player["name"]
        try:
            stats = fetch_player_stats(player["source"], name)
            if stats is None:
                print(f"{name}: no matching player row found; preserving existing stats")
                continue
            results[name] = (stats, player["kind"])
            successes += 1
            print(f"{name}: {build_line(stats, player['kind'])}")
        except Exception as exc:
            print(f"{name}: source unavailable ({exc}); preserving existing stats")

    if successes == 0:
        print("No transfer stats sources returned a matching player row. No site data changed.")
        return 0

    changed = update_index(results)
    print(f"Transfer tracker: {successes}/{len(PLAYERS)} player sources matched.")
    print("Transfer tracker: index.html updated." if changed else "Transfer tracker: no changes needed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
