#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re
from datetime import datetime,timezone,date,timedelta
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parent
DATA=ROOT/"data.json"; OUT=ROOT/"scoreboard"/"scoreboard-data.json"
WEEKS=[
("2026-08-27","2026-08-30","WEEK 0 • AUG 27–30"),("2026-09-03","2026-09-06","WEEK 1 • SEP 3–6"),("2026-09-10","2026-09-13","WEEK 2 • SEP 10–13"),("2026-09-17","2026-09-20","WEEK 3 • SEP 17–20"),("2026-09-24","2026-09-27","WEEK 4 • SEP 24–27"),("2026-10-01","2026-10-04","WEEK 5 • OCT 1–4"),("2026-10-08","2026-10-11","WEEK 6 • OCT 8–11"),("2026-10-15","2026-10-18","WEEK 7 • OCT 15–18"),("2026-10-22","2026-10-25","WEEK 8 • OCT 22–25"),("2026-10-29","2026-11-01","WEEK 9 • OCT 29–NOV 1"),("2026-11-05","2026-11-08","WEEK 10 • NOV 5–8"),("2026-11-12","2026-11-15","WEEK 11 • NOV 12–15"),("2026-11-19","2026-11-22","WEEK 12 • NOV 19–22")]
BIG_SKY=["Montana","Montana State","Idaho","Idaho State","Eastern Washington","Northern Arizona","Northern Colorado","Portland State","Weber State","Southern Utah","Utah Tech","Cal Poly","UC Davis"]
ALIASES={
"montana":{"montana","montanagrizzlies"},"montanastate":{"montanastate","montanastatebobcats"},
"idaho":{"idaho","idahovandals"},"idahostate":{"idahostate","idahostatebengals"},
"easternwashington":{"easternwashington","easternwashingtoneagles"},"northernarizona":{"northernarizona","northernarizonalumberjacks","nau"},
"northerncolorado":{"northerncolorado","northerncoloradobears"},"portlandstate":{"portlandstate","portlandstatevikings"},
"weberstate":{"weberstate","weberstatewildcats"},"southernutah":{"southernutah","southernutahthunderbirds"},
"utahtech":{"utahtech","utahtechtrailblazers"},"calpoly":{"calpoly","calpolymustangs"},"ucdavis":{"ucdavis","ucdavisaggies"}}
HEADERS={}
BASE="https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"
def norm(s): return re.sub(r"[^a-z0-9]","",str(s or "").lower())
def canonical(s):
    n=norm(re.sub(r"\s*\([^)]*\)\s*$","",str(s or "")))
    for k,v in ALIASES.items():
        if n==k or n in v:return k
    return n
def read_rankings():
    d=json.loads(DATA.read_text(encoding="utf-8")); raw=d.get("fcs_top25") or d.get("fcs_top20") or []
    if len(raw)<25: raise RuntimeError(f"Expected 25 rankings, found {len(raw)}")
    out=[]; seen=set()
    for i,x in enumerate(raw[:25],1):
        name=re.sub(r"\s*\([^)]*\)\s*$","",str(x.get("team") or x.get("name") or "")).strip(); key=canonical(name)
        if not name or key in seen: raise RuntimeError(f"Invalid/duplicate ranking: {name}")
        seen.add(key); out.append({"rank":int(x.get("rank") or i),"team":name,"record":x.get("record","")})
    return out
def daterange(a,b):
    d=date.fromisoformat(a); e=date.fromisoformat(b)
    while d<=e: yield d.isoformat(); d+=timedelta(days=1)
def get(params):
    last=None
    for base in (BASE, BASE.replace("https://","http://")):
        try:
            r=requests.get(base,params=params,headers=HEADERS,timeout=30)
            r.raise_for_status()
            p=r.json()
            if not isinstance(p,dict) or not isinstance(p.get("events"),list):
                raise RuntimeError("ESPN response missing events")
            return p["events"]
        except Exception as exc:
            last=exc
    raise RuntimeError(f"ESPN scoreboard request failed: {last}")
def fetch_week(i,start,end,groups=None):
    q={"year":2026,"seasontype":2,"week":i,"limit":1000}
    if groups:q["groups"]=groups
    try:
        e=get(q)
        if e:return e,"week"
    except Exception:pass
    out=[]; seen=set()
    for d in daterange(start,end):
        q={"dates":d.replace("-",""),"limit":1000}
        if groups:q["groups"]=groups
        try:
            for e in get(q):
                k=str(e.get("id") or json.dumps(e,sort_keys=True))
                if k not in seen:seen.add(k);out.append(e)
        except Exception as ex:print("warning",d,ex)
    if not out: raise RuntimeError(f"No ESPN events returned for week {i}")
    return out,"daily"
def compact(ev):
    c=(ev.get("competitions") or [{}])[0]; teams=[]
    for x in c.get("competitors",[]) or []:
        t=x.get("team") or {}
        teams.append({"id":str(t.get("id") or x.get("id") or ""),"name":t.get("displayName") or t.get("shortDisplayName") or t.get("name") or "","short":t.get("shortDisplayName") or t.get("displayName") or t.get("name") or "","abbreviation":t.get("abbreviation") or "","homeAway":x.get("homeAway") or "","score":x.get("score"),"logo":t.get("logo") or ""})
    st=(c.get("status") or {}).get("type") or {}; v=c.get("venue") or {}; a=v.get("address") or {}; b=[]
    for br in c.get("broadcasts",[]) or []:b.extend(br.get("names") or [])
    return {"id":str(ev.get("id") or ""),"date":ev.get("date") or "","name":ev.get("name") or "","shortName":ev.get("shortName") or "","venue":v.get("fullName") or "","city":a.get("city") or "","state":a.get("state") or "","teams":teams,"status":{"state":st.get("state") or "","completed":bool(st.get("completed")),"name":st.get("name") or "","detail":st.get("detail") or "","shortDetail":st.get("shortDetail") or ""},"broadcasts":b[:4]}
def filter_big_sky(events):
    wanted={canonical(x) for x in BIG_SKY}; out=[]; seen=set()
    for e in events:
        if any(canonical(t.get("name") or t.get("short")) in wanted for t in e.get("teams",[])) and e["id"] not in seen:
            seen.add(e["id"]);out.append(e)
    return out
def self_test():
    assert len(read_rankings())==25
    fx=[
      {"id":"a","teams":[{"name":"Dartmouth"},{"name":"Lehigh"}]},
      {"id":"b","teams":[{"name":"Youngstown State"},{"name":"South Dakota State"}]},
      {"id":"c","teams":[{"name":"Austin Peay"},{"name":"West Florida"}]},
      {"id":"d","teams":[{"name":"Montana"},{"name":"Oregon State"}]},
      {"id":"e","teams":[{"name":"Northern Arizona"},{"name":"Utah Tech"}]},
      {"id":"f","teams":[{"name":"Stetson"},{"name":"UC Davis"}]},
      {"id":"x","teams":[{"name":"Eastern Michigan"},{"name":"Wisconsin"}]}]
    assert canonical("South Dakota State")!=canonical("South Dakota")
    assert {e["id"] for e in filter_big_sky(fx)}=={"d","e","f"}
    print("SELF-TEST PASSED")
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--self-test",action="store_true");a=ap.parse_args()
    if a.self_test:return self_test()
    out={"season":2026,"generatedAt":datetime.now(timezone.utc).isoformat(),"source":"ESPN College Football scoreboard API","rankings":read_rankings(),"bigSkyTeams":BIG_SKY,"weeks":[]}
    for i,(s,e,label) in enumerate(WEEKS):
        f,fs=fetch_week(i,s,e,"81"); allx,bs=fetch_week(i,s,e,None)
        fc=[compact(x) for x in f]; bg=filter_big_sky([compact(x) for x in allx])
        out["weeks"].append({"index":i,"start":s,"end":e,"label":label,"complete":True,"fcsSource":fs,"bigSkySource":bs,"fcsEvents":fc,"bigSkyEvents":bg,"fcsEventCount":len(fc),"bigSkyEventCount":len(bg)})
        print(f"{label}: FCS={len(fc)} BigSky={len(bg)}")
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
if __name__=="__main__":main()
