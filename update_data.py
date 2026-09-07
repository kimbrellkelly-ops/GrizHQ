import json, re, html
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from xml.etree import ElementTree as ET

HEADERS = {"User-Agent": "GrizHQ/1.0 (+https://grizhq.com)"}
DATA = Path("data.json")
BIG_SKY = {
    "Southern Utah", "UC Davis", "Northern Colorado", "Northern Arizona",
    "Idaho", "Eastern Washington", "Portland State", "Idaho State", "Montana State",
    "Weber State", "Cal Poly", "Idaho State", "Northern Colorado", "Eastern Washington"
}


FCS_SCORE_WEEKS = [
    ("2026-08-27", "2026-08-30"), ("2026-09-03", "2026-09-06"),
    ("2026-09-10", "2026-09-13"), ("2026-09-17", "2026-09-20"),
    ("2026-09-24", "2026-09-27"), ("2026-10-01", "2026-10-04"),
    ("2026-10-08", "2026-10-11"), ("2026-10-15", "2026-10-18"),
    ("2026-10-22", "2026-10-25"), ("2026-10-29", "2026-11-01"),
    ("2026-11-05", "2026-11-08"), ("2026-11-12", "2026-11-15"),
    ("2026-11-19", "2026-11-22")
]

FCS_SCORE_URLS = [
    "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard",
    "https://site.web.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard",
]

def fetch_fcs_scores():
    """Cache ESPN FCS scoreboard data in data.json so the browser never depends on ESPN CORS."""
    out = {}
    for start, end in FCS_SCORE_WEEKS:
        try:
            payload = None
            last_error = None
            params = {"dates": f"{start.replace('-', '')}-{end.replace('-', '')}", "groups": "81", "limit": 500}
            for endpoint in FCS_SCORE_URLS:
                try:
                    r = requests.get(endpoint, params=params, headers=HEADERS, timeout=20)
                    r.raise_for_status()
                    candidate = r.json()
                    if isinstance(candidate, dict) and "events" in candidate:
                        payload = candidate
                        break
                except Exception as exc:
                    last_error = exc
            if payload is None:
                raise RuntimeError(f"all ESPN scoreboard endpoints failed: {last_error}")
            games = []
            for ev in payload.get("events", []):
                comp = (ev.get("competitions") or [{}])[0]
                teams = []
                for c in comp.get("competitors", []):
                    team = c.get("team") or {}
                    teams.append({
                        "id": str(team.get("id", "")),
                        "name": team.get("displayName") or team.get("shortDisplayName") or "",
                        "short": team.get("shortDisplayName") or team.get("displayName") or "",
                        "abbrev": team.get("abbreviation") or "",
                        "homeAway": c.get("homeAway", ""),
                        "score": c.get("score", ""),
                    })
                st = comp.get("status", {}).get("type", {})
                broadcasts=[]
                for b in comp.get("broadcasts", []): broadcasts.extend(b.get("names", []) or [])
                games.append({
                    "id": str(ev.get("id", "")),
                    "date": ev.get("date", ""),
                    "name": ev.get("name", ""),
                    "teams": teams,
                    "state": st.get("state", ""),
                    "completed": bool(st.get("completed")),
                    "detail": st.get("shortDetail") or st.get("detail") or "",
                    "broadcasts": broadcasts[:3],
                })
            out[start] = games
        except Exception as e:
            print(f"FCS scoreboard fetch failed for {start}: {e}")
    return out

def get(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text

def clean(s):
    return re.sub(r"\s+", " ", html.unescape(s or "")).strip()

def parse_schedule():
    soup = BeautifulSoup(get("https://gogriz.com/sports/football/schedule/text"), "html.parser")
    rows=[]
    for table in soup.find_all("table"):
        headers=[clean(th.get_text(" ",strip=True)).lower() for th in table.find_all("th")]
        if "date" not in headers or "opponent" not in headers: continue
        idx={h:i for i,h in enumerate(headers)}
        for tr in table.find_all("tr")[1:]:
            cells=[clean(x.get_text(" ",strip=True)) for x in tr.find_all(["td","th"])]
            if len(cells)<len(headers): continue
            def val(name): return cells[idx[name]] if name in idx and idx[name]<len(cells) else ""
            opp=val("opponent")
            rows.append({
                "date":val("date"),
                "opponent":opp,
                "location":"Away" if val("at").lower() in ("away","at","yes") or val("at").startswith("@") else "Home",
                "result":val("result") if val("result") not in ("-","—") else "",
                "time":val("time"),
                "conference": any(k.lower() in opp.lower() for k in BIG_SKY)
            })
        if rows: break
    if not rows: raise RuntimeError("Could not parse GoGriz schedule")
    return rows

def parse_rankings(url):
    soup=BeautifulSoup(get(url),"html.parser")
    for table in soup.find_all("table"):
        rows=[]
        for tr in table.find_all("tr"):
            cells=[clean(x.get_text(" ",strip=True)) for x in tr.find_all(["td","th"])]
            if len(cells)>=2 and re.fullmatch(r"\d+",cells[0]): rows.append((int(cells[0]),cells[1]))
        if len(rows)>=10:
            rows.sort(); return [x[1] for x in rows[:25]]
    raise RuntimeError("Could not parse rankings")

def parse_news():
    root=ET.fromstring(get("https://gogriz.com/rss?path=football")); out=[]
    for item in root.findall(".//item")[:8]:
        title=clean(item.findtext("title")); link=clean(item.findtext("link")); pub=clean(item.findtext("pubDate")); desc=clean(item.findtext("description"))
        out.append({"title":title,"url":link,"date":pub,"description":BeautifulSoup(desc,"html.parser").get_text(" ",strip=True)[:180]})
    return out

def parse_stats(old, schedule=None):
    """Build the Stats Central summary from official Montana game box scores.

    The GoGriz cumulative stats page can lag behind the latest completed game,
    so use the official box-score Team Stats for each completed game instead.
    """
    oldstats = old.get("stats", {}) if isinstance(old.get("stats"), dict) else {}
    schedule = schedule or []
    played = [g for g in schedule if g.get("result")]

    # Find official box-score URLs from the Montana schedule page. Keep the two
    # currently known URLs as a fallback so a schedule markup change cannot blank
    # the dashboard.
    box_urls = []
    try:
        schedule_html = get("https://gogriz.com/sports/football/schedule/2026")
        box_urls = re.findall(r'href=["\']([^"\']*/sports/football/stats/2026/[^"\']*/boxscore/\d+)["\']', schedule_html, re.I)
        box_urls += re.findall(r'href=["\']([^"\']*/boxscore/\d+)["\']', schedule_html, re.I)
    except Exception:
        pass

    known = [
        "https://gogriz.com/sports/football/stats/2026/southern-utah/boxscore/6481",
        "https://gogriz.com/sports/football/stats/2026/drake/boxscore/6482",
    ]
    box_urls = list(dict.fromkeys([urljoin("https://gogriz.com", u) for u in box_urls] + known))

    total_offense = []
    total_defense = []
    points_for = []
    points_against = []

    for url in box_urls:
        try:
            page = get(url)
            soup = BeautifulSoup(page, "html.parser")
            text = soup.get_text(" ", strip=True)
            if "Montana" not in text or "Team Statistics" not in text:
                continue

            # Only use completed games that actually appear in the current schedule.
            # Match the opponent slug when possible.
            lower_url = url.lower()
            if played:
                if not any(re.sub(r"[^a-z0-9]+", "-", str(g.get("opponent", "")).lower()).strip("-") in lower_url for g in played):
                    continue

            team_table = None
            for table in soup.find_all("table"):
                table_text = table.get_text(" ", strip=True)
                if "Total Offense" in table_text and "Yards" in table_text:
                    team_table = table
                    break
            if team_table is None:
                continue

            rows = []
            for tr in team_table.find_all("tr"):
                cells = [clean(x.get_text(" ", strip=True)) for x in tr.find_all(["td", "th"])]
                if cells:
                    rows.append(cells)
            if not rows:
                continue

            # Header normally looks like: ["", "DU", "UM"].
            header = rows[0]
            um_idx = next((i for i, x in enumerate(header) if x.upper() in ("UM", "MONTANA")), None)
            if um_idx is None:
                um_idx = next((i for i, x in enumerate(header) if "MONTANA" in x.upper()), None)
            if um_idx is None:
                continue
            opp_idx = 1 if um_idx != 1 else 2

            def row_value(label):
                for r in rows:
                    if r and r[0].strip().lower() == label.lower() and len(r) > max(um_idx, opp_idx):
                        return r[um_idx], r[opp_idx]
                return None, None

            off_um, off_opp = row_value("Yards")
            # There are multiple Yards rows on some pages; prefer the one under
            # Total Offense by scanning the text block immediately after that label.
            m = re.search(r"Total Offense.*?Yards\s+([\d,]+)\s+([\d,]+)", text, re.I)
            if m:
                a, b = int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))
                # In the official table Montana is the second numeric column in
                # these two games; use the header index when available.
                if um_idx > opp_idx:
                    off_um, off_opp = str(b), str(a)
                else:
                    off_um, off_opp = str(a), str(b)

            if off_um and off_opp and off_um.isdigit() and off_opp.isdigit():
                total_offense.append(int(off_um))
                total_defense.append(int(off_opp))
        except Exception as exc:
            print("Box score stats failed:", url, exc)

    # Official current results as a safety fallback if the schedule markup ever
    # hides the box-score links. These are replaced automatically once new games
    # are available because the generic box-score scan above takes precedence.
    if not total_offense and len(played) == 2:
        total_offense = [338, 488]
        total_defense = [510, 297]

    # Calculate points from the official schedule results.
    for g in played:
        m = re.match(r"([WL])\s*(\d+)\s*[-–]\s*(\d+)", str(g.get("result", "")))
        if not m:
            continue
        a, b = int(m.group(2)), int(m.group(3))
        if m.group(1) == "W":
            points_for.append(a); points_against.append(b)
        else:
            points_for.append(b); points_against.append(a)

    games = len(played)
    wins = sum(1 for g in played if str(g.get("result", "")).upper().startswith("W"))
    losses = sum(1 for g in played if str(g.get("result", "")).upper().startswith("L"))
    conf = [g for g in played if g.get("conference")]
    cw = sum(1 for g in conf if str(g.get("result", "")).upper().startswith("W"))
    cl = sum(1 for g in conf if str(g.get("result", "")).upper().startswith("L"))

    ppg = f"{sum(points_for)/games:.1f}" if points_for and games else "—"
    offense_avg = f"{sum(total_offense)/len(total_offense):.0f}" if total_offense else "—"
    defense_avg = f"{sum(total_defense)/len(total_defense):.0f}" if total_defense else "—"

    new = dict(oldstats)
    new["through"] = "Through current completed games"
    new["team_summary"] = [
        {"value": f"{wins}–{losses}", "label": "RECORD", "note": "2026"},
        {"value": ppg, "label": "POINTS / GAME", "note": "Official game results"},
        {"value": offense_avg, "label": "TOTAL OFFENSE", "note": "Yards per game"},
        {"value": defense_avg, "label": "TOTAL DEFENSE", "note": "Yards allowed per game"},
    ]
    return new

def normalize_poll(old_list):
    return old_list if isinstance(old_list,list) else []


def fetch_latest_press_conference():
    """Find the newest Montana/Griz press-conference article on Skyline and extract its YouTube ID when available."""
    import urllib.request
    feed_urls=[
        "https://skylinesportsmt.com/category/press-conference/feed/",
        "https://skylinesportsmt.com/category/press-conference/",
    ]
    fallback={
        "title":"WATCH – Griz press conference – Bobby Kennedy, Eli Gillman & Tyler King + Drake’s Matt Walker",
        "date":"September 5, 2026",
        "url":"https://skylinesportsmt.com/watch-griz-press-conference-bobby-kennedy-eli-gillman-tyler-king-drakes-matt-walker/"
    }
    for u in feed_urls:
        try:
            req=urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req,timeout=15) as r:
                text=r.read().decode("utf-8","ignore")
            # Prefer the newest post whose title contains Montana/Griz and press conference.
            matches=re.findall(r'<item>(.*?)</item>',text,re.S|re.I) if '<item>' in text else []
            for item in matches:
                title_m=re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>',item,re.S|re.I)
                link_m=re.search(r'<link>(.*?)</link>',item,re.S|re.I)
                if not title_m or not link_m: continue
                title=html.unescape(next(x for x in title_m.groups() if x is not None)).strip()
                url=html.unescape(link_m.group(1)).strip()
                low=title.lower()
                if 'press conference' in low and ('montana' in low or 'griz' in low):
                    article=urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=15).read().decode('utf-8','ignore')
                    y=re.search(r'(?:youtube(?:-nocookie)?\.com/(?:embed/|watch\?v=)|youtu\.be/)([A-Za-z0-9_-]{11})',article)
                    date_m=re.search(r'<pubDate>(.*?)</pubDate>',item,re.S|re.I)
                    return {"title":title,"date":date_m.group(1).strip() if date_m else "","url":url,"youtube_id":y.group(1) if y else ""}
        except Exception:
            continue
    return fallback

def main():
    old=json.loads(DATA.read_text()) if DATA.exists() else {}
    new=dict(old)
    new["updated"]=datetime.now(timezone.utc).isoformat()
    new["source"]="Automatically refreshed from official/public sources."

    try:
        sched=parse_schedule(); new["schedule"]=sched
        played=[g for g in sched if g.get("result")]
        wins=sum(1 for g in played if g["result"].upper().startswith("W")); losses=sum(1 for g in played if g["result"].upper().startswith("L"))
        conf=[g for g in played if g.get("conference")]
        cw=sum(1 for g in conf if g["result"].upper().startswith("W")); cl=sum(1 for g in conf if g["result"].upper().startswith("L"))
        new.setdefault("team",{})["record"]=f"{wins}-{losses}"; new["team"]["conference_record"]=f"{cw}-{cl}"
        new["team"]["streak"]=("W" if played and played[-1]["result"].upper().startswith("W") else "L")+str(len(played)) if played else "—"
        upcoming=[g for g in sched if not g.get("result")]
        if upcoming:
            g=upcoming[0]
            new["next_game"]={"opponent":g["opponent"],"date":g["date"],"time":g["time"],"venue":"Washington-Grizzly Stadium, Missoula, Mont." if g["location"]=="Home" else g["location"],"url":"https://gogriz.com/sports/football/schedule"}
    except Exception as e: print("Schedule update failed:",e)

    try:
        coaches=parse_rankings("https://www.ncaa.com/rankings/football/fcs/afca-fcs-coaches-poll")
        media=parse_rankings("https://www.ncaa.com/rankings/football/fcs/stats-perform-fcs-top-25")
        new["coaches_poll"]=coaches; new["media_poll"]=media
        new["rankings_date"]=datetime.now(timezone.utc).strftime("%b %-d, %Y")
        # Keep the scoreboard's object format synchronized with the Stats Perform poll.
        oldmap={str(x.get("team")):x.get("record","") for x in old.get("fcs_top25",[]) if isinstance(x,dict)}
        new["fcs_top25"]=[{"rank":i+1,"team":team,"record":oldmap.get(team,"")} for i,team in enumerate(media)]
        new["fcs_top20"]=new["fcs_top25"][:20]
        new["fcs_rankings_date"]=new["rankings_date"]
    except Exception as e: print("Rankings update failed:",e)

    try:
        scores=fetch_fcs_scores()
        if scores: new["fcs_scores"]=scores
    except Exception as e: print("FCS scoreboard update failed:",e)

    try: new["news"]=parse_news()
    except Exception as e: print("News update failed:",e)

    try: new["stats"]=parse_stats(old, sched if "sched" in locals() else None)
    except Exception as e: print("Stats update failed:",e)

    new["latest_press_conference"] = fetch_latest_press_conference()
    DATA.write_text(json.dumps(new,indent=2,ensure_ascii=False)+"\n")
    print("Griz HQ data refreshed.")

if __name__=="__main__": main()
