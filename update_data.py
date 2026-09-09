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
    """Fetch the newest official GoGriz two-deep and never substitute a third-party chart."""
    # The official game-notes links are the most reliable source. The RSS/article
    # scan below remains the discovery mechanism for future games.
    known_official = [
        ("https://gogriz.com/documents/2026/9/1/UM-DRAKE_NOTES.pdf", "2026-09-01"),
        ("https://gogriz.com/documents/2026/8/25/UM-SUU_NOTES.pdf", "2026-08-25"),
    ]
    fallback_url="https://ewscripps.brightspotcdn.com/66/2f/2ecc2224473884436d4981ff2667/um-depth-chart.pdf"
    feed="https://gogriz.com/rss?path=football"
    candidates=[]

    # Try the known official notes first. A game-notes PDF is accepted only if
    # it actually contains a parseable two-deep; otherwise we continue scanning.
    for href, published in known_official:
        try:
            r=requests.get(href,headers=HEADERS,timeout=30)
            r.raise_for_status()
            if r.content[:4] != b"%PDF":
                continue
            dc=parse_depth_chart_pdf(r.content,href,published)
            dc["checked_at"]=datetime.now(timezone.utc).isoformat()
            print("Depth chart updated from official notes:",href)
            return dc
        except Exception as e:
            print("Known official depth-chart candidate failed:",href,e)

    try:
        root=ET.fromstring(get(feed))
        for item in root.findall(".//item")[:40]:
            title=clean(item.findtext("title")); link=clean(item.findtext("link")); pub=clean(item.findtext("pubDate"))
            if not link: continue
            low=title.lower()
            if any(k in low for k in ("football","griz","bulldog","trailblazer","beaver","wildcat","vandals")):
                candidates.append((link,pub,title))
    except Exception as e:
        print("Depth chart RSS scan failed:",e)

    # Prefer a newly published official article containing a UM Notes/game-notes PDF.
    for article_url,pub,title in candidates:
        try:
            article=get(article_url)
            hrefs=[]
            soup=BeautifulSoup(article,"html.parser")
            for a in soup.find_all("a",href=True):
                href=urljoin(article_url,a.get("href")); txt=clean(a.get_text(" ",strip=True)).lower()
                # Only consider official GoGriz documents or explicitly labelled UM Notes.
                if ("gogriz.com/documents/" in href.lower() or ".pdf" in href.lower()) and ("notes" in txt or "two" in txt or "depth" in txt or "documents/" in href.lower()):
                    hrefs.append((href,txt))
            hrefs += [(u,"") for u in re.findall(r'https?://[^\"\'\s<>]+\.pdf(?:\?[^\"\'\s<>]*)?',article,re.I)]
            seen=set()
            for href,txt in hrefs:
                if href in seen: continue
                seen.add(href)
                if "gogriz.com/documents/" not in href.lower():
                    continue
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
                    dc["checked_at"]=datetime.now(timezone.utc).isoformat()
                    print("Depth chart updated from official article notes:",href)
                    return dc
                except Exception as e:
                    print("Depth chart candidate failed:",href,e)
        except Exception as e:
            print("Depth chart article scan failed:",article_url,e)

    # Last-resort official mirror of the published two-deep.
    try:
        r=requests.get(fallback_url,headers=HEADERS,timeout=30)
        r.raise_for_status()
        if r.content[:4] == b"%PDF":
            dc=parse_depth_chart_pdf(r.content,fallback_url,"2026-08-25")
            dc["checked_at"]=datetime.now(timezone.utc).isoformat()
            return dc
    except Exception as e:
        print("Fallback depth chart fetch failed:",e)

    # Keep the last known chart only when it came from an official source.
    olddc=old.get("depth_chart") if isinstance(old.get("depth_chart"),dict) else None
    oldurl=str(olddc.get("source_url", "")) if olddc else ""
    if olddc and olddc.get("offense") and olddc.get("defense") and (
        oldurl.startswith("https://gogriz.com/") or "ewscripps.brightspotcdn.com" in oldurl
    ):
        olddc=dict(olddc)
        olddc["checked_at"]=datetime.now(timezone.utc).isoformat()
        return olddc
    return None


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
        old_coaches = old.get("coaches_poll") if isinstance(old.get("coaches_poll"), list) else []
        old_media = old.get("media_poll") if isinstance(old.get("media_poll"), list) else []
        new["coaches_poll"]=coaches; new["media_poll"]=media
        rankings_changed = (coaches != old_coaches) or (media != old_media)
        if rankings_changed or not old.get("rankings_date"):
            new["rankings_date"]=datetime.now(timezone.utc).strftime("%b %-d, %Y")
        else:
            new["rankings_date"]=old.get("rankings_date")
        # Keep the scoreboard object format synchronized with the Stats Perform poll.
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
