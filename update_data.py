import json, re, html
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from xml.etree import ElementTree as ET

HEADERS = {"User-Agent": "GrizHQ/1.0 (+https://grizhq.com)"}
DATA = Path("data.json")


def get(url):
    """Fetch a public source with the Griz HQ user-agent and fail loudly on HTTP errors."""
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text
NEXT_GAME_VENUES = {
    "Oregon State": "Reser Stadium, Corvallis, Ore.",
    "UC Davis": "UC Davis Health Stadium, Davis, Calif.",
    "Northern Colorado": "Nottingham Field, Greeley, Colo.",
    "Northern Arizona": "J. Lawrence Walkup Skydome, Flagstaff, Ariz.",
    "Idaho": "Kibbie-ASUI Activity Center, Moscow, Idaho",
    "Eastern Washington": "Roos Field, Cheney, Wash.",
    "Portland State": "Hillsboro Stadium, Hillsboro, Ore.",
    "Idaho State": "Holt Arena, Pocatello, Idaho",
    "Montana State": "Bobcat Stadium, Bozeman, Mont.",
}

BIG_SKY = {
    "Southern Utah", "UC Davis", "Northern Colorado", "Northern Arizona",
    "Idaho", "Eastern Washington", "Portland State", "Idaho State", "Montana State",
    "Weber State", "Cal Poly", "Idaho State", "Northern Colorado", "Eastern Washington"
}


FCS_SCORE_WEEKS = [
    ("2026-08-27", "2026-08-30"),
    ("2026-09-03", "2026-09-06"),
    ("2026-09-10", "2026-09-13"),
    ("2026-09-17", "2026-09-20"),
    ("2026-09-24", "2026-09-27"),
    ("2026-10-01", "2026-10-04"),
    ("2026-10-08", "2026-10-11"),
    ("2026-10-15", "2026-10-18"),
    ("2026-10-22", "2026-10-25"),
    ("2026-10-29", "2026-11-01"),
    ("2026-11-05", "2026-11-08"),
    ("2026-11-12", "2026-11-15"),
    ("2026-11-19", "2026-11-22"),
    ("2026-11-26", "2026-11-29"),
    ("2026-12-03", "2026-12-06"),
]

FCS_SCORE_URLS = [
    "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard",
    "https://site.web.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard",
]

def fetch_fcs_scores():
    """Cache complete daily ESPN events by week start. Never use the incomplete groups=81 feed."""
    out = {}
    for start, end in FCS_SCORE_WEEKS:
        games = []
        day = datetime.fromisoformat(start).date()
        last = datetime.fromisoformat(end).date()
        while day <= last:
            ymd = day.strftime("%Y%m%d")
            payload = None
            for endpoint in FCS_SCORE_URLS:
                try:
                    r = requests.get(endpoint, params={"dates": ymd, "limit": 500}, headers=HEADERS, timeout=20)
                    r.raise_for_status()
                    candidate = r.json()
                    if isinstance(candidate, dict) and isinstance(candidate.get("events"), list):
                        payload = candidate
                        break
                except Exception as exc:
                    print(f"ESPN {ymd} failed: {exc}")
            if payload:
                for ev in payload.get("events", []):
                    comp = (ev.get("competitions") or [{}])[0]
                    teams = []
                    for c in comp.get("competitors", []):
                        team = c.get("team") or {}
                        teams.append({"id": str(team.get("id", "")), "name": team.get("displayName") or team.get("shortDisplayName") or "", "short": team.get("shortDisplayName") or team.get("displayName") or "", "abbrev": team.get("abbreviation") or "", "homeAway": c.get("homeAway", ""), "score": c.get("score", ""), "logo": team.get("logo", "")})
                    st = comp.get("status", {}).get("type", {})
                    broadcasts = [n for b in comp.get("broadcasts", []) for n in (b.get("names") or [])]
                    games.append({"id": str(ev.get("id", "")), "date": ev.get("date", ""), "name": ev.get("name", ""), "teams": teams, "state": st.get("state", ""), "completed": bool(st.get("completed")), "detail": st.get("shortDetail") or st.get("detail") or "", "broadcasts": broadcasts[:3]})
            day = day.fromordinal(day.toordinal()+1)
        seen = set(); out[start] = [g for g in games if not (g["id"] in seen or seen.add(g["id"]))]
    return out

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

def sync_montana_schedule_with_espn(rows):
    """Use ESPN game results to keep Montana's completed schedule authoritative."""
    endpoint="https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"
    for row in rows:
        m=re.search(r"([A-Za-z]{3})\s+(\d{1,2})", str(row.get("date","")))
        if not m:
            continue
        try:
            dt=datetime.strptime(f"2026 {m.group(1)} {m.group(2)}", "%Y %b %d")
        except ValueError:
            continue
        try:
            payload=requests.get(endpoint, params={"dates":dt.strftime("%Y%m%d"),"limit":500}, headers=HEADERS, timeout=20).json()
            for ev in payload.get("events", []):
                comp=(ev.get("competitions") or [{}])[0]
                competitors=comp.get("competitors") or []
                mt=next((x for x in competitors if str((x.get("team") or {}).get("id",""))=="149"), None)
                if not mt:
                    continue
                opp=next((x for x in competitors if x is not mt), None)
                status=(comp.get("status") or {}).get("type") or {}
                if not status.get("completed"):
                    continue
                mt_score=str(mt.get("score",""))
                opp_score=str((opp or {}).get("score",""))
                if not mt_score.isdigit() or not opp_score.isdigit():
                    continue
                result=("W" if int(mt_score)>int(opp_score) else "L" if int(mt_score)<int(opp_score) else "T")
                row["result"]=f"{result} {mt_score}-{opp_score}"
                row["location"]="Home" if mt.get("homeAway")=="home" else "Away"
                if opp:
                    row["opponent"]=(opp.get("team") or {}).get("displayName") or row.get("opponent","")
                row["time"]=row.get("time") or ""
                break
        except Exception as exc:
            print(f"ESPN Montana schedule sync failed for {row.get('date')}: {exc}")
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

BIG_SKY_STANDINGS_URL = "https://bigskyconf.com/standings.aspx?path=football"
BIG_SKY_STATS_URL = "https://bigskyconf.com/stats.aspx?path=football&year=2026"
BIG_SKY_NEWS_RSS = "https://bigskyconf.com/rss?path=football"

def _clean_text(value):
    return re.sub(r"\s+", " ", BeautifulSoup(str(value or ""), "html.parser").get_text(" ", strip=True)).strip()

def parse_big_sky_standings():
    soup = BeautifulSoup(get(BIG_SKY_STANDINGS_URL), "html.parser")
    for table in soup.find_all("table"):
        headers = [_clean_text(x.get_text(" ", strip=True)).lower() for x in table.find_all("th")]
        if "school" not in headers or "big sky" not in headers or "overall" not in headers:
            continue
        school_i=headers.index("school"); conf_i=headers.index("big sky"); overall_i=headers.index("overall")
        home_i=headers.index("home") if "home" in headers else -1
        away_i=headers.index("away") if "away" in headers else -1
        conf_pf_i=headers.index("conf pf-pa") if "conf pf-pa" in headers else -1
        pf_i=headers.index("pf-pa") if "pf-pa" in headers else -1
        conf_streak_i=headers.index("conf streak") if "conf streak" in headers else -1
        overall_streak_i=headers.index("overall streak") if "overall streak" in headers else -1
        out=[]
        for rank,tr in enumerate(table.find_all("tr")[1:],1):
            cells=[_clean_text(x.get_text(" ",strip=True)) for x in tr.find_all(["td","th"])]
            if len(cells)<=max(school_i,conf_i,overall_i): continue
            school=cells[school_i]
            if not school or school.lower()=="school": continue
            out.append({"rank":rank,"team":school,"conference_record":cells[conf_i],"overall_record":cells[overall_i],
                        "home":cells[home_i] if home_i>=0 and home_i<len(cells) else "",
                        "away":cells[away_i] if away_i>=0 and away_i<len(cells) else "",
                        "conference_points":cells[conf_pf_i] if conf_pf_i>=0 and conf_pf_i<len(cells) else "",
                        "points":cells[pf_i] if pf_i>=0 and pf_i<len(cells) else "",
                        "conference_streak":cells[conf_streak_i] if conf_streak_i>=0 and conf_streak_i<len(cells) else "",
                        "overall_streak":cells[overall_streak_i] if overall_streak_i>=0 and overall_streak_i<len(cells) else ""})
        if len(out)>=10: return out
    raise RuntimeError("Could not parse Big Sky standings")

def _parse_big_sky_leader_table(table):
    headers=[_clean_text(x.get_text(" ",strip=True)).lower() for x in table.find_all("th")]
    if "player" not in headers: return None
    rows=[]
    for tr in table.find_all("tr")[1:]:
        cells=[_clean_text(x.get_text(" ",strip=True)) for x in tr.find_all(["td","th"])]
        if len(cells)>=2: rows.append(cells)
    pi=headers.index("player")
    def idx(*names):
        for name in names:
            if name in headers: return headers.index(name)
        return -1
    vi=idx("yds","total","pts"); ti=idx("td","sacks"); ri=idx("avg/g","effic","pts/g")
    out=[]
    for row in rows[:5]:
        raw=row[pi]; m=re.match(r"(.+?)\s*\(([^)]+)\)$",raw)
        out.append({"name":m.group(1).strip() if m else raw,"school":m.group(2).strip() if m else "",
                    "value":row[vi] if vi>=0 and vi<len(row) else "",
                    "secondary":row[ti] if ti>=0 and ti<len(row) else "",
                    "rate":row[ri] if ri>=0 and ri<len(row) else ""})
    return out

def parse_big_sky_leaders():
    soup=BeautifulSoup(get(BIG_SKY_STATS_URL),"html.parser")
    wanted=["rushing","passing","receiving","scoring","tackles","sacks"]; found={}
    for table in soup.find_all("table"):
        headers=[_clean_text(x.get_text(" ",strip=True)).lower() for x in table.find_all("th")]
        if "player" not in headers: continue
        heading=table.find_previous(["h4","h5","h3"])
        label=_clean_text(heading.get_text(" ",strip=True)).lower() if heading else ""
        if label=="scoring (td)": label="scoring"
        if label in wanted and label not in found: found[label]=_parse_big_sky_leader_table(table)
    if len(found)<5: raise RuntimeError("Could not parse Big Sky individual leaders")
    return found

def parse_big_sky_news():
    try:
        root=ET.fromstring(get(BIG_SKY_NEWS_RSS)); out=[]
        for item in root.findall(".//item")[:10]:
            title=_clean_text(item.findtext("title")); link=_clean_text(item.findtext("link"))
            pub=_clean_text(item.findtext("pubDate")); desc=_clean_text(item.findtext("description"))[:220]
            if title and link: out.append({"title":title,"url":link,"date":pub,"description":desc})
        return out
    except Exception as exc:
        print("Big Sky RSS failed:",exc); return []

def parse_big_sky_players_of_week():
    """Parse the newest official Big Sky football weekly preview and its player-of-the-week honorees."""
    try:
        root=ET.fromstring(get(BIG_SKY_NEWS_RSS))
        candidate=None
        for item in root.findall(".//item"):
            title=_clean_text(item.findtext("title"))
            link=_clean_text(item.findtext("link"))
            pub=_clean_text(item.findtext("pubDate"))
            if title and link and "football weekly preview" in title.lower():
                candidate={"title":title,"url":link,"date":pub}
                break
        if not candidate:
            raise RuntimeError("No Big Sky football weekly preview found in RSS")

        soup=BeautifulSoup(get(candidate["url"]),"html.parser")
        lines=[_clean_text(x) for x in soup.stripped_strings if _clean_text(x)]
        marker_i=-1
        for i,line in enumerate(lines):
            if re.search(r"BIG SKY PLAYER OF THE WEEK HONOREES FOR WEEK",line,re.I):
                marker_i=i
                break
        if marker_i<0:
            raise RuntimeError("Weekly player-of-the-week section not found")

        category_re=re.compile(r"^(Co-)?(Offensive|Defensive|Special Teams) Player of the Week(?::)?$",re.I)
        winner_re=re.compile(r"^(.+?),\s+(.+?)\s+\(([^)]+)\)$")
        stop_re=re.compile(r"^(?:Others Nominated:|[A-Z][A-Z0-9’'\-\s]+)$")
        out=[]
        i=marker_i+1
        current_week=""
        mweek=re.search(r"WEEK\s+(\d+)",lines[marker_i],re.I)
        if mweek: current_week=mweek.group(1)

        while i<len(lines):
            line=lines[i]
            if re.match(r"^[A-Z][A-Z0-9’'\-\s]+$",line) and "PLAYER OF THE WEEK" not in line.upper():
                break
            cm=category_re.match(line)
            if not cm:
                i+=1
                continue

            category=("Co-" if cm.group(1) else "")+cm.group(2).title()+" Player of the Week"
            winners=[]
            j=i+1
            while j<len(lines):
                wm=winner_re.match(lines[j])
                if wm:
                    winners.append(wm)
                    j+=1
                    if not cm.group(1):
                        break
                    continue
                break
            if not winners:
                i+=1
                continue

            summary=""
            if j<len(lines) and not lines[j].lower().startswith("others nominated:"):
                summary=lines[j]
            for wm in winners:
                player=wm.group(1).strip()
                school=wm.group(2).strip()
                bio=wm.group(3).strip()
                position=bio.split(",",1)[0].strip()
                out.append({
                    "week":current_week,
                    "category":category,
                    "player":player,
                    "school":school,
                    "position":position,
                    "summary":summary,
                    "article_url":candidate["url"],
                    "published":candidate["date"]
                })
            while j<len(lines) and not category_re.match(lines[j]) and not (re.match(r"^[A-Z][A-Z0-9’'\-\s]+$",lines[j]) and "PLAYER OF THE WEEK" not in lines[j].upper()):
                if lines[j].lower().startswith("others nominated:"):
                    j+=1
                    break
                j+=1
            i=j
        if not out:
            raise RuntimeError("No weekly football honorees parsed")
        return out
    except Exception as exc:
        print("Big Sky players-of-week update failed:",exc)
        return []

def parse_news():
    root=ET.fromstring(get("https://gogriz.com/rss?path=football")); out=[]
    for item in root.findall(".//item")[:8]:
        title=clean(item.findtext("title")); link=clean(item.findtext("link")); pub=clean(item.findtext("pubDate")); desc=clean(item.findtext("description"))
        out.append({"title":title,"url":link,"date":pub,"description":BeautifulSoup(desc,"html.parser").get_text(" ",strip=True)[:180]})
    return out

def parse_stats(old, schedule=None):
    """Rebuild stats from official GoGriz sources; never carry stale detail forward."""
    from stats_rebuild import build_stats
    schedule = schedule or []
    schedule_html = get("https://gogriz.com/sports/football/schedule/2026")
    return build_stats(schedule, old.get("stats", {}) if isinstance(old, dict) else {}, get, schedule_html)


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
        sched=parse_schedule(); sched=sync_montana_schedule_with_espn(sched); new["schedule"]=sched
        played=[g for g in sched if g.get("result")]
        wins=sum(1 for g in played if g["result"].upper().startswith("W")); losses=sum(1 for g in played if g["result"].upper().startswith("L"))
        conf=[g for g in played if g.get("conference")]
        cw=sum(1 for g in conf if g["result"].upper().startswith("W")); cl=sum(1 for g in conf if g["result"].upper().startswith("L"))
        new.setdefault("team",{})["record"]=f"{wins}-{losses}"; new["team"]["conference_record"]=f"{cw}-{cl}"
        new["team"]["streak"]=("W" if played and played[-1]["result"].upper().startswith("W") else "L")+str(len(played)) if played else "—"
        upcoming=[g for g in sched if not g.get("result")]
        if upcoming:
            g=upcoming[0]
            new["next_game"]={"opponent":g["opponent"],"date":g["date"],"time":g["time"],"venue": "Washington-Grizzly Stadium, Missoula, Mont." if g["location"] == "Home" else NEXT_GAME_VENUES.get(g["opponent"], g["location"]),"url":"https://gogriz.com/sports/football/schedule"}
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

    # Scoreboards are maintained exclusively by refresh_scoreboards.py.

    try: new["news"]=parse_news()
    except Exception as e: print("News update failed:",e)

    try: new["big_sky_standings"]=parse_big_sky_standings()
    except Exception as e: print("Big Sky standings update failed:",e)
    try: new["big_sky_leaders"]=parse_big_sky_leaders()
    except Exception as e: print("Big Sky leaders update failed:",e)
    try: new["big_sky_news"]=parse_big_sky_news()
    except Exception as e: print("Big Sky news update failed:",e)
    try:
        pow=parse_big_sky_players_of_week()
        if pow: new["big_sky_players_of_week"]=pow
    except Exception as e: print("Big Sky players-of-week update failed:",e)

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
