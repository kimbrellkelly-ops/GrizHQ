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
    If a stats section changes shape upstream, keep the previous good dashboard."""
    soup=BeautifulSoup(get("https://gogriz.com/sports/football/stats/2026"),"html.parser")
    text=soup.get_text("\n",strip=True)
    m=re.search(r"Team Statistics \(([^)]+)\)",text)
    if not m: raise RuntimeError("Team Statistics block not found")
    record=m.group(1)
    # Pull the Montana/Opponents columns from the visible team-stat table.
    team_table=None
    for t in soup.find_all("table"):
        st=t.get_text(" ",strip=True)
        if "Points Per Game" in st and "Total Offense" in st:
            team_table=t; break
    if team_table is None: raise RuntimeError("Team stats table not found")
    rows={}
    for tr in team_table.find_all("tr"):
        c=[clean(x.get_text(" ",strip=True)) for x in tr.find_all(["td","th"])]
        if len(c)>=3: rows[c[0]]=c[1:]
    def pair(label, default="—"):
        v=rows.get(label, [default,default]); return v[0] if v else default
    ppg=pair("Points Per Game"); total=pair("Total"); total_yards=pair("Total Yards")
    avg_play=pair("Average Per Play"); pass_total=pair("Total", "—")
    # The table has duplicate labels; use section-aware text regex for key values.
    def after(section,label,default="—"):
        pat=rf"{re.escape(section)}.*?{re.escape(label)}\\s+([^\\s]+)"
        mm=re.search(pat,text,re.S|re.I)
        return mm.group(1) if mm else default
    rush_avg=after("Rushing","Avg. Per Game")
    pass_avg=after("Passing","Avg. Per Game")
    total_avg=after("Total Offense","Avg. Per Game")
    opp_total=after("Total Offense","Total Yards")
    turnover_line=after("Miscellaneous","Fumbles-Lost")
    oldstats=old.get("stats",{}) if isinstance(old.get("stats"),dict) else {}
    new=dict(oldstats)
    new["through"]="Current 2026 cumulative stats"
    new["team_summary"]= [
        {"value":record.replace(", ","–"),"label":"RECORD","note":"2026"},
        {"value":ppg,"label":"POINTS / GAME","note":"Official cumulative stats"},
        {"value":total_avg if total_avg!="—" else total_yards,"label":"TOTAL OFFENSE","note":"Per game"},
        {"value":opp_total,"label":"TOTAL DEFENSE","note":"Yards allowed"}
    ]
    # Preserve the existing detailed cards unless we can safely derive values.
    new.setdefault("offense",oldstats.get("offense",[])); new.setdefault("defense",oldstats.get("defense",[]))
    return new

def normalize_poll(old_list):
    return old_list if isinstance(old_list,list) else []

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

    try: new["news"]=parse_news()
    except Exception as e: print("News update failed:",e)

    try: new["stats"]=parse_stats(old)
    except Exception as e: print("Stats update failed:",e)

    DATA.write_text(json.dumps(new,indent=2,ensure_ascii=False)+"\n")
    print("Griz HQ data refreshed.")

if __name__=="__main__": main()
