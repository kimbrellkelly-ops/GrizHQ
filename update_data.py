import json, re, html, sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from xml.etree import ElementTree as ET

HEADERS = {"User-Agent": "GrizHQ/1.0 (+https://grizhq.com)"}
DATA = Path("data.json")

def get(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text

def clean(s):
    return re.sub(r"\s+", " ", html.unescape(s or "")).strip()

def parse_schedule():
    url = "https://gogriz.com/sports/football/schedule/text"
    soup = BeautifulSoup(get(url), "html.parser")
    rows = []
    # The GoGriz text schedule is rendered as a table. Find the table with Date/Opponent.
    for table in soup.find_all("table"):
        headers = [clean(th.get_text(" ", strip=True)).lower() for th in table.find_all("th")]
        if "date" not in headers or "opponent" not in headers:
            continue
        idx = {h:i for i,h in enumerate(headers)}
        for tr in table.find_all("tr")[1:]:
            cells = [clean(x.get_text(" ", strip=True)) for x in tr.find_all(["td","th"])]
            if len(cells) < len(headers): continue
            def val(name):
                return cells[idx[name]] if name in idx and idx[name] < len(cells) else ""
            rows.append({
                "date": val("date"),
                "opponent": val("opponent"),
                "location": "Away" if val("at").lower() in ("away","at","yes") or val("at").startswith("@") else "Home",
                "result": val("result"),
                "time": val("time"),
                "conference": "big sky" in val("tournament").lower() if "tournament" in idx else False
            })
        if rows: break
    if not rows:
        raise RuntimeError("Could not parse GoGriz schedule")
    return rows

def parse_rankings(url):
    soup = BeautifulSoup(get(url), "html.parser")
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [clean(x.get_text(" ", strip=True)) for x in tr.find_all(["td","th"])]
            if len(cells) >= 2 and re.fullmatch(r"\d+", cells[0]):
                rows.append((int(cells[0]), cells[1]))
        if len(rows) >= 10:
            rows.sort()
            return [x[1] for x in rows[:20]]
    raise RuntimeError("Could not parse rankings")

def parse_news():
    xml = get("https://gogriz.com/rss?path=football")
    root = ET.fromstring(xml)
    out = []
    for item in root.findall(".//item")[:8]:
        title = clean(item.findtext("title"))
        link = clean(item.findtext("link"))
        pub = clean(item.findtext("pubDate"))
        desc = clean(item.findtext("description"))
        out.append({"title": title, "url": link, "date": pub, "description": BeautifulSoup(desc, "html.parser").get_text(" ", strip=True)[:180]})
    return out

def main():
    old = json.loads(DATA.read_text()) if DATA.exists() else {}
    new = dict(old)
    new["updated"] = datetime.now(timezone.utc).isoformat()
    new["source"] = "Automatically refreshed from official/public sources."

    try:
        sched = parse_schedule()
        new["schedule"] = sched
        record = [g for g in sched if g.get("result")]
        wins = sum(1 for g in record if g["result"].upper().startswith("W"))
        losses = sum(1 for g in record if g["result"].upper().startswith("L"))
        conf = [g for g in record if g.get("conference")]
        cw = sum(1 for g in conf if g["result"].upper().startswith("W"))
        cl = sum(1 for g in conf if g["result"].upper().startswith("L"))
        new["team"]["record"] = f"{wins}-{losses}"
        new["team"]["conference_record"] = f"{cw}-{cl}"
        upcoming = [g for g in sched if not g.get("result")]
        if upcoming:
            g = upcoming[0]
            new["next_game"] = {
                "opponent": g["opponent"], "date": g["date"], "time": g["time"],
                "venue": "Washington-Grizzly Stadium, Missoula, Mont." if g["location"] == "Home" else g["location"],
                "url": "https://godrakebulldogs.com/sports/football" if "drake" in g["opponent"].lower() else "https://gogriz.com/sports/football/schedule"
            }
    except Exception as e:
        print("Schedule update failed:", e)

    try:
        new["coaches_poll"] = parse_rankings("https://www.ncaa.com/rankings/football/fcs/afca-fcs-coaches-poll")
        new["rankings_date"] = datetime.now(timezone.utc).strftime("%b %-d, %Y")
    except Exception as e:
        print("Coaches poll update failed:", e)

    try:
        new["media_poll"] = parse_rankings("https://www.ncaa.com/rankings/football/fcs/stats-perform-fcs-top-25")
    except Exception as e:
        print("Media poll update failed:", e)

    try:
        new["news"] = parse_news()
    except Exception as e:
        print("News update failed:", e)

    DATA.write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n")
    print("Griz HQ data refreshed.")

if __name__ == "__main__":
    main()
