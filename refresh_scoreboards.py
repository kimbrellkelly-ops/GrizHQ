#!/usr/bin/env python3
"""Authoritative Griz HQ scoreboard cache.

Sources:
  ESPN FCS scoreboard group 81
  ESPN Big Sky scoreboard group 20

The browser never queries ESPN. GitHub Actions builds scoreboard/scoreboard-data.json.
"""
from __future__ import annotations
import argparse, json, re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data.json"
OUT = ROOT / "scoreboard" / "scoreboard-data.json"

WEEKS = [
    ("2026-08-27","2026-08-30","WEEK 0 • AUG 27–30"),
    ("2026-09-03","2026-09-06","WEEK 1 • SEP 3–6"),
    ("2026-09-10","2026-09-13","WEEK 2 • SEP 10–13"),
    ("2026-09-17","2026-09-20","WEEK 3 • SEP 17–20"),
    ("2026-09-24","2026-09-27","WEEK 4 • SEP 24–27"),
    ("2026-10-01","2026-10-04","WEEK 5 • OCT 1–4"),
    ("2026-10-08","2026-10-11","WEEK 6 • OCT 8–11"),
    ("2026-10-15","2026-10-18","WEEK 7 • OCT 15–18"),
    ("2026-10-22","2026-10-25","WEEK 8 • OCT 22–25"),
    ("2026-10-29","2026-11-01","WEEK 9 • OCT 29–NOV 1"),
    ("2026-11-05","2026-11-08","WEEK 10 • NOV 5–8"),
    ("2026-11-12","2026-11-15","WEEK 11 • NOV 12–15"),
    ("2026-11-19","2026-11-22","WEEK 12 • NOV 19–22"),
    ("2026-11-26","2026-11-29","WEEK 13 • NOV 26–29"),
    ("2026-12-03","2026-12-06","WEEK 14 • DEC 3–6"),
]
BIG_SKY_TEAMS = [
    "Montana", "Montana State", "Idaho", "Idaho State", "Eastern Washington",
    "Northern Arizona", "Northern Colorado", "Portland State", "Weber State",
    "Southern Utah", "Utah Tech", "Cal Poly", "UC Davis",
]
# ESPN team IDs are included only as optional exact-match metadata when available.
BIG_SKY_IDS = {"149","147","70","304","331","2464","2458","279","2692","253","3101","13","302"}
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36"}
ENDPOINTS = [
    "https://site.web.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard",
    "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard",
]

def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())

def canonical(s: str) -> str:
    n = norm(s)
    aliases = {
        "montanagrizzlies":"montana", "montanastatebobcats":"montanastate",
        "idahovandals":"idaho", "idahostatebengals":"idahostate",
        "easternwashingtoneagles":"easternwashington", "northernarizonalumberjacks":"northernarizona",
        "northerncoloradobears":"northerncolorado", "portlandstatevikings":"portlandstate",
        "weberstatewildcats":"weberstate", "southernutahthunderbirds":"southernutah",
        "utahtechtrailblazers":"utahtech", "calpolymustangs":"calpoly", "ucdavisaggies":"ucdavis",
        "southdakotastatejackrabbits":"southdakotastate", "southdakotacoyotes":"southdakota",
    }
    return aliases.get(n, n)

def load_rankings() -> list[dict[str, Any]]:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    raw = data.get("fcs_top25") or data.get("fcs_top20") or []
    if len(raw) < 25:
        raise RuntimeError(f"Expected 25 FCS rankings, found {len(raw)}")
    out, seen = [], set()
    for i, row in enumerate(raw[:25], 1):
        team = re.sub(r"\s*\([^)]*\)\s*$", "", str(row.get("team") or row.get("name") or "")).strip()
        key = canonical(team)
        if not team or key in seen:
            raise RuntimeError(f"Invalid or duplicate ranked team at #{i}: {team!r}")
        seen.add(key)
        out.append({"rank": int(row.get("rank") or i), "team": team, "record": row.get("record", "")})
    return out

def date_range(start: str, end: str):
    d, e = date.fromisoformat(start), date.fromisoformat(end)
    while d <= e:
        yield d.isoformat()
        d += timedelta(days=1)

def get_events(params: dict[str, Any]) -> list[dict[str, Any]]:
    last = None
    for endpoint in ENDPOINTS:
        try:
            r = requests.get(endpoint, params=params, headers=HEADERS, timeout=30)
            r.raise_for_status()
            payload = r.json()
            events = payload.get("events") if isinstance(payload, dict) else None
            if isinstance(events, list):
                return events
        except Exception as exc:
            last = exc
    raise RuntimeError(f"ESPN request failed: {last}")

def fetch_group_week(start: str, end: str, group: str) -> tuple[list[dict[str, Any]], str]:
    all_events: dict[str, dict[str, Any]] = {}
    sources = []
    for d in date_range(start, end):
        params = {"dates": d.replace("-", ""), "limit": 500, "groups": group}
        try:
            events = get_events(params)
            sources.append(d)
            for ev in events:
                key = str(ev.get("id") or "")
                if key:
                    all_events[key] = ev
        except Exception as exc:
            print(f"warning: group {group}, {d}: {exc}")
    if not sources:
        raise RuntimeError(f"No ESPN responses for group {group}, {start}–{end}")
    return list(all_events.values()), "ESPN group " + group + " daily fetch"

def compact(ev: dict[str, Any]) -> dict[str, Any]:
    comp = (ev.get("competitions") or [{}])[0]
    st = (comp.get("status") or {}).get("type") or {}
    venue = comp.get("venue") or {}
    address = venue.get("address") or {}
    teams = []
    for c in comp.get("competitors") or []:
        t = c.get("team") or {}
        teams.append({
            "id": str(t.get("id") or c.get("id") or ""),
            "name": t.get("displayName") or t.get("shortDisplayName") or t.get("name") or "",
            "short": t.get("shortDisplayName") or t.get("displayName") or t.get("name") or "",
            "abbreviation": t.get("abbreviation") or "",
            "homeAway": c.get("homeAway") or "",
            "score": c.get("score"),
            "logo": t.get("logo") or "",
        })
    broadcasts = []
    for b in comp.get("broadcasts") or []:
        broadcasts.extend(b.get("names") or [])
    return {
        "id": str(ev.get("id") or ""),
        "date": ev.get("date") or "",
        "name": ev.get("name") or "",
        "shortName": ev.get("shortName") or "",
        "venue": venue.get("fullName") or "",
        "city": address.get("city") or "",
        "state": address.get("state") or "",
        "teams": teams,
        "status": {
            "state": st.get("state") or "",
            "completed": bool(st.get("completed")),
            "name": st.get("name") or "",
            "detail": st.get("detail") or "",
            "shortDetail": st.get("shortDetail") or "",
        },
        "broadcasts": broadcasts[:4],
    }

def validate_big_sky(events: list[dict[str, Any]]):
    allowed_names = {canonical(x) for x in BIG_SKY_TEAMS}
    bad = []
    for ev in events:
        ts = ev.get("teams", [])
        ok = any(str(t.get("id")) in BIG_SKY_IDS or canonical(t.get("name")) in allowed_names for t in ts)
        if not ok:
            bad.append(ev.get("name") or ev.get("id"))
    if bad:
        raise RuntimeError("Big Sky source returned non-Big-Sky event(s): " + ", ".join(map(str, bad[:5])))

def validate_fcs(events: list[dict[str, Any]]):
    for ev in events:
        if len(ev.get("teams", [])) < 2:
            raise RuntimeError(f"Malformed FCS event {ev.get('id')}")

def self_test():
    rankings = load_rankings()
    assert len(rankings) == 25
    assert canonical("South Dakota State") == "southdakotastate"
    assert canonical("South Dakota") == "southdakota"
    assert canonical("South Dakota State") != canonical("South Dakota")
    sample = [compact({"id":"x","date":"2026-09-19T00:00:00Z","competitions":[{"competitors":[
        {"homeAway":"home","team":{"id":"147","displayName":"Montana State Bobcats"},"score":"0"},
        {"homeAway":"away","team":{"id":"12345","displayName":"Central Connecticut State Blue Devils"},"score":"0"}
    ],"status":{"type":{"state":"pre","completed":False}}}]})]
    validate_big_sky(sample)
    validate_fcs(sample)
    print("SELF-TEST PASSED: rankings, South Dakota identity, Big Sky source guard, event structure")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--self-test", action="store_true"); args = ap.parse_args()
    if args.self_test:
        self_test(); return
    rankings = load_rankings()
    weeks = []
    for i, (start, end, label) in enumerate(WEEKS):
        fcs_raw, fcs_source = fetch_group_week(start, end, "81")
        bs_raw, bs_source = fetch_group_week(start, end, "20")
        fcs = [compact(x) for x in fcs_raw]
        bs = [compact(x) for x in bs_raw]
        validate_fcs(fcs); validate_big_sky(bs)
        weeks.append({"index":i,"start":start,"end":end,"label":label,"complete":True,
                      "fcsSource":fcs_source,"bigSkySource":bs_source,
                      "fcsEvents":fcs,"bigSkyEvents":bs,
                      "fcsEventCount":len(fcs),"bigSkyEventCount":len(bs)})
        print(f"{label}: FCS={len(fcs)} Big Sky={len(bs)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"season":2026,"generatedAt":datetime.now(timezone.utc).isoformat(),
                              "source":"ESPN FCS group 81 + Big Sky group 20","rankings":rankings,
                              "bigSkyTeams":BIG_SKY_TEAMS,"weeks":weeks}, indent=2, ensure_ascii=False)+"\n",encoding="utf-8")

if __name__ == "__main__": main()
