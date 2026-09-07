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
            game_center=""
            for a in tr.find_all("a", href=True):
                href=urljoin("https://gogriz.com", a.get("href", ""))
                if "/game-center/" in href or "/boxscore/" in href:
                    game_center=href
                    break
            rows.append({
                "date":val("date"),
                "opponent":opp,
                "location":"Away" if val("at").lower() in ("away","at","yes") or val("at").startswith("@") else "Home",
                "result":val("result") if val("result") not in ("-","—") else "",
                "time":val("time"),
                "conference": any(k.lower() in opp.lower() for k in BIG_SKY),
                "game_center":game_center
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

def attach_game_centers(schedule):
    """Attach official Game Center URLs in schedule order. The text schedule omits link URLs."""
    try:
        soup=BeautifulSoup(get("https://gogriz.com/sports/football/schedule"),"html.parser")
        urls=[]
        for a in soup.find_all("a", href=True):
            label=clean(a.get_text(" ",strip=True)).lower()
            href=urljoin("https://gogriz.com",a.get("href",""))
            if label == "game center" and "/game-center/" in href:
                urls.append(href)
        for i,g in enumerate(schedule):
            if i < len(urls): g["game_center"]=urls[i]
    except Exception as e:
        print("Game center link map failed:",e)
    return schedule

def parse_game_center_totals(url):
    """Read Montana and opponent total yards from an individual official game center."""
    if not url: return None
    try:
        soup=BeautifulSoup(get(url),"html.parser")
        for table in soup.find_all("table"):
            rows=[]
            for tr in table.find_all("tr"):
                cells=[clean(x.get_text(" ",strip=True)) for x in tr.find_all(["td","th"]) ]
                if cells: rows.append(cells)
            joined=" ".join(" ".join(r) for r in rows)
            if "Rushing Yards" not in joined or "Passing Yards" not in joined or "Plays-Yards" not in joined:
                continue
            for row in rows:
                if row and row[0].lower() in ("plays-yards","plays–yards") and len(row)>=3:
                    vals=row[1:]
                    def yards(v):
                        m=re.search(r"-(\d+)$",v.replace(",",""))
                        return int(m.group(1)) if m else None
                    nums=[yards(v) for v in vals]
                    nums=[n for n in nums if n is not None]
                    if len(nums)>=2:
                        # Official game-center team-stats tables list opponent first and Montana second.
                        return {"opponent_yards":nums[0],"montana_yards":nums[-1]}
        return None
    except Exception as e:
        print("Game center stats failed:",url,e)
        return None

def parse_stats(old, schedule=None, current_record=""):
    """Build the Stats summary using the current team record and official game centers.
    The cumulative GoGriz page can lag after a Saturday game, so never let its stale
    record or defense overwrite the current schedule-driven values.
    """
    oldstats=old.get("stats",{}) if isinstance(old.get("stats"),dict) else {}
    new=dict(oldstats)
    if not current_record:
        current_record=str((old.get("team") or {}).get("record") or "")

    # First try official game centers for completed games. This gives true cumulative
    # totals even when the season cumulative page is temporarily one game behind.
    played=schedule or old.get("schedule") or []
    completed=[g for g in played if g.get("result")]
    opponent_yards=[]
    montana_yards=[]
    for g in completed:
        r=parse_game_center_totals(g.get("game_center",""))
        if r:
            opponent_yards.append(r["opponent_yards"])
            montana_yards.append(r["montana_yards"])

    # Fallback to the cumulative page for any values we can safely read.
    try:
        soup=BeautifulSoup(get("https://gogriz.com/sports/football/stats/2026"),"html.parser")
        text=soup.get_text("\n",strip=True)
        m=re.search(r"Team Statistics \(([^)]+)\)",text)
        source_record=m.group(1).split(",",1)[0].strip() if m else ""
        team_table=None
        for t in soup.find_all("table"):
            st=t.get_text(" ",strip=True)
            if "Points Per Game" in st and "Total Offense" in st:
                team_table=t; break
        rows={}
        if team_table is not None:
            for tr in team_table.find_all("tr"):
                c=[clean(x.get_text(" ",strip=True)) for x in tr.find_all(["td","th"])]
                if len(c)>=3: rows[c[0]]=c[1:]
        def pair(label, default="—"):
            v=rows.get(label,[default,default]); return v[0] if v else default
        ppg=pair("Points Per Game")
        total_avg=pair("Avg. Per Game")
        total_yards_cols=rows.get("Total Yards",["—","—"])
        source_opp_yards=total_yards_cols[1] if len(total_yards_cols)>1 else "—"
    except Exception as e:
        print("Cumulative stats fetch failed:",e)
        source_record=ppg=total_avg=source_opp_yards="—"

    games=len(opponent_yards)
    if games:
        defense=f"{sum(opponent_yards)/games:.0f}"
        offense=f"{sum(montana_yards)/games:.0f}"
        # Points per game comes from the actual schedule results and is therefore
        # current even if the cumulative page is stale.
        points=[]
        for g in completed:
            mscore=re.search(r"(?:W|L)\s*(\d+)\s*[-–]",g.get("result",""))
            if mscore: points.append(int(mscore.group(1)))
        ppg=f"{sum(points)/len(points):.1f}" if points else ppg
    else:
        defense=source_opp_yards
        offense=total_avg

    # Keep the detailed player/situational cards already maintained by Griz HQ.
    new["through"]="Current 2026 cumulative stats"
    new["team_summary"]=[
        {"value":str(current_record).replace(", ","–"),"label":"RECORD","note":"2026"},
        {"value":ppg,"label":"POINTS / GAME","note":"Official cumulative stats"},
        {"value":offense,"label":"TOTAL OFFENSE","note":"Yards per game"},
        {"value":defense,"label":"TOTAL DEFENSE","note":"Yards allowed per game"}
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
        sched=parse_schedule(); sched=attach_game_centers(sched); new["schedule"]=sched
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

    try: new["stats"]=parse_stats(old, sched if "sched" in locals() else None, new.get("team",{}).get("record", ""))
    except Exception as e: print("Stats update failed:",e)

    new["latest_press_conference"] = fetch_latest_press_conference()
    DATA.write_text(json.dumps(new,indent=2,ensure_ascii=False)+"\n")
    print("Griz HQ data refreshed.")

if __name__=="__main__": main()
