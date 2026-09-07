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

def parse_stats(old):
    """Refresh the core stats dashboard from the official 2026 cumulative stats page.
    The GoGriz Team Statistics table contains Montana and Opponents as adjacent
    columns. Parse those columns directly so Total Defense is always derived
    from the opponents' Total Offense average, and format the record cleanly.
    """
    soup=BeautifulSoup(get("https://gogriz.com/sports/football/stats/2026"),"html.parser")
    text=soup.get_text("\n",strip=True)
    m=re.search(r"Team Statistics \((\d+)-(\d+),\s*(\d+)-(\d+)\)", text)
    if not m:
        raise RuntimeError("Team Statistics record block not found")
    wins, losses, cw, cl = m.groups()

    team_table=None
    for t in soup.find_all("table"):
        st=t.get_text(" ",strip=True)
        if "Points Per Game" in st and "Total Offense" in st and "Avg. Per Game" in st:
            team_table=t
            break
    if team_table is None:
        raise RuntimeError("Team stats table not found")

    # Sidearm's table uses rows like: Label | Montana | Opponents.
    # Keep the current section so duplicate labels such as Total/Avg. Per Game
    # can be interpreted correctly.
    section=""
    rows={}
    for tr in team_table.find_all("tr"):
        cells=[clean(x.get_text(" ",strip=True)) for x in tr.find_all(["td","th"])]
        if not cells:
            continue
        label=cells[0]
        if label in {"Scoring","First Downs","Rushing","Passing","Total Offense","Returns","Kicking","Penalties","Time Of Possession","Miscellaneous"}:
            section=label
            continue
        if len(cells)>=3:
            rows[(section,label)] = (cells[1],cells[2])

    def pair(section_name, label, default=("—","—")):
        return rows.get((section_name,label), default)

    ppg_m, ppg_o = pair("Scoring","Points Per Game")
    total_off_m, total_off_o = pair("Total Offense","Avg. Per Game")
    total_yards_m, total_yards_o = pair("Total Offense","Total Yards")
    if total_off_m == "—":
        total_off_m = total_yards_m
    if total_off_o == "—":
        total_off_o = total_yards_o

    oldstats=old.get("stats",{}) if isinstance(old.get("stats"),dict) else {}
    new=dict(oldstats)
    new["through"]="Current 2026 cumulative stats"
    new["team_summary"]=[
        {"value":f"{wins}–{losses} • {cw}–{cl} BIG SKY","label":"RECORD","note":"2026"},
        {"value":ppg_m,"label":"POINTS / GAME","note":"Official cumulative stats"},
        {"value":total_off_m,"label":"TOTAL OFFENSE","note":"Yards per game"},
        {"value":total_off_o,"label":"TOTAL DEFENSE","note":"Yards allowed per game"}
    ]

    # Keep the existing detailed cards, comparison table, leaders, game log,
    # etc. intact; those are maintained by the rest of the data pipeline.
    new.setdefault("offense",oldstats.get("offense",[]))
    new.setdefault("defense",oldstats.get("defense",[]))
    return new


def _clean_depth_name(name):
    name=re.sub(r"\s+", " ", name or "").strip(" .")
    name=re.sub(r"\s+-OR\s*$", "", name, flags=re.I)
    return name


def _extract_depth_players_from_line(line):
    """Extract one or more jersey/name pairs from a PDF text line."""
    out=[]
    pat=r"(?<!\d)(\d{1,2})\s+([A-Za-z][A-Za-z’'\-\. ]+?)(?=\s+\d+-\d+\b)"
    for m in re.finditer(pat, line):
        name=_clean_depth_name(m.group(2))
        if name and len(name.split()) >= 2:
            out.append(name)
    return out


def _depth_position(text):
    """Map the 2026 Griz two-deep PDF headings to the site's stable position labels."""
    t=clean(text).upper().replace("–","-")
    mappings=[
        ("WIDE RECEIVER (X)","WR-X"),("WIDE RECEIVER (Z)","WR-Z"),("WIDE RECEIVER (F)","WR-F"),
        ("TIGHT END","TE"),("QUARTERBACK","QB"),("TAILBACK","RB"),
        ("LEFT TACKLE","LT"),("LEFT GUARD","LG"),("CENTER","C"),
        ("RIGHT GUARD","RG"),("RIGHT TACKLE","RT"),
        ("NOSE","NT"),("ELEPHANT","DE"),("DEFENSIVE END","DL"),
        ("BUCK (LB)","BUCK"),("BUCK","BUCK"),("SAM (LB)","LB-SAM"),("SAM","LB-SAM"),
        ("MIKE (LB)","LB-MIKE"),("MIKE","LB-MIKE"),("WILL (LB)","LB-WILL"),("WILL","LB-WILL"),
        ("CORNERBACK","CB"),("FREE SAFETY","S"),("GRIZ (NICKEL)","S"),("BOUNDARY SAFETY","S"),
        ("PUNTER","P"),("KICKER","K"),("PUNT RETURN","PR"),("KICKOFF RETURN","KR"),
        ("HOLDER","H"),("SNAPPER","LS")
    ]
    for needle, pos in mappings:
        if t == needle or t.startswith(needle+" "):
            return pos
    return None


def parse_depth_chart_pdf(pdf_bytes, source_url, published=""):
    """Parse the one-page Montana two-deep PDF while preserving the site's existing schema."""
    try:
        import pdfplumber
        from io import BytesIO
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            if not pdf.pages:
                raise RuntimeError("depth chart PDF has no pages")
            page=pdf.pages[0]
            words=page.extract_words(keep_blank_chars=False, use_text_flow=False)
            if not words:
                raise RuntimeError("depth chart PDF contains no text")

            # The current Griz one-page sheet has three vertical columns: offense, defense, specialists.
            columns={"offense":[],"defense":[],"special_teams":[]}
            for w in words:
                x=float(w.get("x0",0)); top=float(w.get("top",0))
                col="offense" if x < 380 else ("defense" if x < 710 else "special_teams")
                columns[col].append((top,x,w.get("text", "")))

            parsed={k:[] for k in columns}
            position_order={k:[] for k in columns}
            active={k:None for k in columns}
            stop={k:False for k in columns}

            # Group words into visual rows, then walk each column top-to-bottom.
            for col, items in columns.items():
                items.sort(key=lambda z:(z[0],z[1]))
                rows=[]
                for item in items:
                    if not rows or abs(item[0]-rows[-1][0])>2.5:
                        rows.append([item[0],[(item[1],item[2])]])
                    else:
                        rows[-1][1].append((item[1],item[2]))
                for top, rowwords in rows:
                    row=" ".join(t for _,t in sorted(rowwords,key=lambda z:z[0])).strip()
                    normrow=clean(row).upper()
                    if normrow.startswith("PRONUNCIATION"):
                        stop[col]=True
                        active[col]=None
                        continue
                    if stop[col]:
                        continue
                    pos=_depth_position(row)
                    if pos:
                        active[col]=pos
                        position_order[col].append(pos)
                        parsed[col].append({"position":pos,"_players":[]})
                        continue
                    if not active[col]:
                        continue
                    players=_extract_depth_players_from_line(row)
                    if players:
                        parsed[col][-1]["_players"].extend(players)

            def finalize(section):
                out=[]
                for row in parsed[section]:
                    players=[]
                    for name in row.get("_players",[]):
                        if name not in players: players.append(name)
                    if not players: continue
                    item={"position":row["position"],"first":players[0],"second":players[1] if len(players)>1 else "—"}
                    if len(players)>2:
                        item["also"]=" / ".join(players[2:])
                    out.append(item)
                return out

            offense=finalize("offense")
            defense=finalize("defense")
            special=finalize("special_teams")
            if len(offense)<8 or len(defense)<8 or len(special)<3:
                raise RuntimeError(f"depth chart parse incomplete: offense={len(offense)} defense={len(defense)} special={len(special)}")
            return {
                "source":"Official Montana two-deep / GoGriz game notes",
                "source_url":source_url,
                "published":published or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "note":"Automatically refreshed from the latest published Montana two-deep. If the official source is temporarily unavailable, the last good chart is retained.",
                "offense":offense,
                "defense":defense,
                "special_teams":special,
            }
    except Exception as e:
        raise RuntimeError(f"depth chart parse failed: {e}") from e


def fetch_depth_chart(old):
    """Find the newest 2026 GoGriz football notes PDF containing a two-deep and safely update it."""
    fallback_url="https://ewscripps.brightspotcdn.com/66/2f/2ecc2224473884436d4981ff2667/um-depth-chart.pdf"
    feed="https://gogriz.com/rss?path=football"
    candidates=[]
    try:
        root=ET.fromstring(get(feed))
        for item in root.findall(".//item")[:30]:
            title=clean(item.findtext("title")); link=clean(item.findtext("link")); pub=clean(item.findtext("pubDate"))
            if not link: continue
            low=title.lower()
            if any(k in low for k in ("football","griz","bulldog","trailblazer","beaver","wildcat","vandals")):
                candidates.append((link,pub,title))
    except Exception as e:
        print("Depth chart RSS scan failed:",e)

    # Prefer a newly published article with a notes/depth PDF. Scan newest first.
    for article_url,pub,title in candidates:
        try:
            article=get(article_url)
            if not re.search(r"two[- ]deep|depth chart|depth[- ]chart", article, re.I) and "notes" not in article.lower():
                continue
            hrefs=[]
            soup=BeautifulSoup(article,"html.parser")
            for a in soup.find_all("a",href=True):
                href=urljoin(article_url,a.get("href")); txt=clean(a.get_text(" ",strip=True)).lower()
                if ".pdf" in href.lower() or "notes" in txt or "game notes" in txt:
                    hrefs.append((href,txt))
            hrefs += [(u,"") for u in re.findall(r'https?://[^\"\'\s<>]+\.pdf(?:\?[^\"\'\s<>]*)?',article,re.I)]
            seen=set()
            for href,txt in hrefs:
                if href in seen: continue
                seen.add(href)
                if not ("pdf" in href.lower() or "notes" in txt or "two" in txt or "depth" in txt): continue
                try:
                    r=requests.get(href,headers=HEADERS,timeout=30)
                    r.raise_for_status()
                    if r.content[:4] != b"%PDF": continue
                    dt=""
                    try:
                        from email.utils import parsedate_to_datetime
                        dt=parsedate_to_datetime(pub).date().isoformat() if pub else ""
                    except Exception: pass
                    dc=parse_depth_chart_pdf(r.content,href,dt)
                    print("Depth chart updated from:",href)
                    return dc
                except Exception as e:
                    print("Depth chart candidate failed:",href,e)
        except Exception as e:
            print("Depth chart article scan failed:",article_url,e)

    # Known-good current 2026 two-deep source. This keeps the chart alive even when RSS/article scanning changes upstream.
    try:
        r=requests.get(fallback_url,headers=HEADERS,timeout=30)
        r.raise_for_status()
        if r.content[:4] == b"%PDF":
            return parse_depth_chart_pdf(r.content,fallback_url,"2026-08-25")
    except Exception as e:
        print("Fallback depth chart fetch failed:",e)

    olddc=old.get("depth_chart") if isinstance(old.get("depth_chart"),dict) else None
    if olddc and olddc.get("offense") and olddc.get("defense"):
        return olddc
    return None

def normalize_poll(old_list):
    return old_list if isinstance(old_list,list) else []


def _is_montana_state_press_title(title):
    """Return True for Montana State/Bobcats press items that must never enter the Griz feed."""
    low = str(title or "").lower().strip()
    if "bobcats" in low or "bozeman" in low:
        return True
    if re.search(r"\bmontana\s+(?:state|st\.?)\b", low):
        return True
    return False

def fetch_latest_press_conference():
    """Find the newest Montana/Griz press-conference article on Skyline and extract its YouTube ID when available, excluding Montana State/Bobcats."""
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
                # Skyline's press-conference feed mixes Griz and Bobcat items.
                # Never allow Montana State/Bobcats/Bozeman into the Griz slot.
                if _is_montana_state_press_title(title):
                    continue
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

    try: new["stats"]=parse_stats(old)
    except Exception as e: print("Stats update failed:",e)

    try:
        depth=fetch_depth_chart(old)
        if depth:
            new["depth_chart"]=depth
    except Exception as e:
        print("Depth chart update failed; retaining last good chart:",e)

    new["latest_press_conference"] = fetch_latest_press_conference()
    DATA.write_text(json.dumps(new,indent=2,ensure_ascii=False)+"\n")
    print("Griz HQ data refreshed.")

if __name__=="__main__": main()
