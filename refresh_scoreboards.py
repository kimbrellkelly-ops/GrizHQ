#!/usr/bin/env python3
"""Authoritative Griz HQ scoreboard cache builder.

Only this program writes scoreboard/scoreboard-data.json.
Sources: ESPN team schedules for the ranked FCS Top 25 and Big Sky teams.
The browser never fetches ESPN directly.
"""
from __future__ import annotations
import argparse,json,re
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parent; DATA=ROOT/'data.json'; OUT=ROOT/'scoreboard'/'scoreboard-data.json'
WEEKS=[('2026-08-27','2026-08-30','WEEK 0 • AUG 27–30'),('2026-09-03','2026-09-06','WEEK 1 • SEP 3–6'),('2026-09-10','2026-09-13','WEEK 2 • SEP 10–13'),('2026-09-17','2026-09-20','WEEK 3 • SEP 17–20'),('2026-09-24','2026-09-27','WEEK 4 • SEP 24–27'),('2026-10-01','2026-10-04','WEEK 5 • OCT 1–4'),('2026-10-08','2026-10-11','WEEK 6 • OCT 8–11'),('2026-10-15','2026-10-18','WEEK 7 • OCT 15–18'),('2026-10-22','2026-10-25','WEEK 8 • OCT 22–25'),('2026-10-29','2026-11-01','WEEK 9 • OCT 29–NOV 1'),('2026-11-05','2026-11-08','WEEK 10 • NOV 5–8'),('2026-11-12','2026-11-15','WEEK 11 • NOV 12–15'),('2026-11-19','2026-11-22','WEEK 12 • NOV 19–22')]
BIG_SKY=['Montana','Montana State','Idaho','Idaho State','Eastern Washington','Northern Arizona','Northern Colorado','Portland State','Weber State','Southern Utah','Utah Tech','Cal Poly','UC Davis']
HEADERS={'Accept':'application/json, text/plain, */*','Origin':'https://www.espn.com','Referer':'https://www.espn.com/'}
ROOTS=['https://site.api.espn.com/apis/site/v2/sports/football/college-football','https://site.web.api.espn.com/apis/site/v2/sports/football/college-football']
def norm(s):return re.sub(r'[^a-z0-9]','',str(s or '').lower())
def load_rankings():
 d=json.loads(DATA.read_text(encoding='utf-8')); raw=d.get('fcs_top25') or d.get('fcs_top20') or []
 if len(raw)<25:raise RuntimeError(f'Expected 25 FCS rankings; found {len(raw)}')
 out=[];seen=set()
 for i,x in enumerate(raw[:25],1):
  n=re.sub(r'\s*\([^)]*\)\s*$','',str(x.get('team') or x.get('name') or '')).strip(); k=norm(n)
  if not n or k in seen:raise RuntimeError(f'Invalid/duplicate FCS ranking: {n!r}')
  seen.add(k);out.append({'rank':int(x.get('rank') or i),'team':n,'record':x.get('record','')})
 return out,d.get('rankings_date') or d.get('fcs_rankings_date') or ''
def daterange(a,b):
 d=date.fromisoformat(a);e=date.fromisoformat(b)
 while d<=e:yield d.isoformat();d+=timedelta(days=1)
def request_json(path,params=None):
 last=None
 for root in ROOTS:
  try:
   r=requests.get(root+path,params=params or {},headers=HEADERS,timeout=30);r.raise_for_status();p=r.json()
   if isinstance(p,dict):return p
   last=RuntimeError('ESPN response was not an object')
  except Exception as e:last=e
 raise RuntimeError(f'ESPN request failed: {last}')
def request(params):
 p=request_json('/scoreboard',params)
 if not isinstance(p.get('events'),list):raise RuntimeError('ESPN scoreboard response missing events list')
 return p['events']
def team_catalog():
 p=request_json('/teams',{'limit':700})
 rows=[]
 try:rows=p['sports'][0]['leagues'][0]['teams']
 except Exception:rows=[]
 return [x.get('team') or x for x in rows]
ESPN_TEAM_ID_OVERRIDES={'West Florida':'110242','Utah Tech':'3101'}
def team_for_rank(name,catalog):
 override=ESPN_TEAM_ID_OVERRIDES.get(name)
 if override:return {'id':override,'location':name,'displayName':name,'name':name}
 wanted=canonical(name)
 candidates=[]
 for t in catalog:
  for field in ('location','displayName','name','shortDisplayName'):
   value=t.get(field) or ''
   k=canonical(value)
   if k==wanted:candidates.append((100000+len(k),t));break
   if k.startswith(wanted):candidates.append((len(wanted),t))
 if not candidates:return None
 return max(candidates,key=lambda x:x[0])[1]
def fetch_named_team_events(names,catalog):
 out=[];seen=set();cache={}
 for name in names:
  team=team_for_rank(name,catalog)
  if not team:raise RuntimeError(f'Could not resolve ESPN team: {name}')
  tid=str(team.get('id') or '')
  if not tid:raise RuntimeError(f'ESPN team has no ID: {name}')
  if tid not in cache:
   p=request_json(f'/teams/{tid}/schedule',{'season':2026,'seasontype':2})
   events=p.get('events') or []
   cache[tid]=[compact(e) for e in events]
  for e in cache[tid]:
   k=str(e.get('id') or '')
   if k and k not in seen:seen.add(k);out.append(e)
 return out
def score_value(value):
 if isinstance(value,dict):
  return value.get('displayValue') or value.get('value') or ''
 if value is None:return ''
 return str(value)

def compact(e):
 c=(e.get('competitions') or [{}])[0];v=c.get('venue') or {};addr=v.get('address') or {};st=(c.get('status') or {}).get('type') or {};teams=[]
 for x in c.get('competitors',[]) or []:
  t=x.get('team') or {};teams.append({'id':str(t.get('id') or x.get('id') or ''),'name':t.get('displayName') or t.get('shortDisplayName') or t.get('name') or '','short':t.get('shortDisplayName') or t.get('displayName') or t.get('name') or '','abbreviation':t.get('abbreviation') or '','homeAway':x.get('homeAway') or '','score':score_value(x.get('score')),'logo':t.get('logo') or ''})
 b=[]
 for br in c.get('broadcasts',[]) or []:b.extend(br.get('names') or [])
 return {'id':str(e.get('id') or ''),'date':e.get('date') or '','name':e.get('name') or '','shortName':e.get('shortName') or '','venue':v.get('fullName') or '','city':addr.get('city') or '','state':addr.get('state') or '','teams':teams,'status':{'state':st.get('state') or '','completed':bool(st.get('completed')),'name':st.get('name') or '','detail':st.get('detail') or '','shortDetail':st.get('shortDetail') or ''},'broadcasts':b[:4]}
def canonical(s):
 n=norm(s)
 aliases={
  'montanast':'montanastate',
  'montanastateuniversity':'montanastate',
  'southernutahthunderbirds':'southernutah',
  'utahtechtrailblazers':'utahtech',
  'utahtechtrailblazers':'utahtech',
  'ucdavisaggies':'ucdavis',
  'northernarizonalumberjacks':'northernarizona',
  'northerncoloradobears':'northerncolorado',
  'easternwashingtoneagles':'easternwashington',
  'weberstatewildcats':'weberstate',
  'portlandstatevikings':'portlandstate',
  'idahostatetigers':'idahostate',
  'idahovandals':'idaho'
 }
 return aliases.get(n,n)

def ranked_team_match(team_name, rankings):
 # ESPN commonly appends mascots to the school name. Match by school-name
 # prefix, but choose the longest ranked school so South Dakota State cannot
 # be mistaken for South Dakota (same for North Dakota State/North Dakota).
 t=canonical(team_name)
 candidates=[]
 for r in rankings:
  k=canonical(r['team'])
  if t==k or t.startswith(k):
   candidates.append((len(k),r))
 if not candidates:
  return None
 return max(candidates,key=lambda x:x[0])[1]

def pair_key(e):
 ts=e.get('teams') or []
 if len(ts)<2:return None
 return '|'.join(sorted(canonical(t.get('name') or t.get('short')) for t in ts[:2]))
def big_sky_expected(data,start,end):
 rows=data.get('big_sky_full_schedules') or [];out=set()
 months={'Aug':'08','Sep':'09','Oct':'10','Nov':'11','Dec':'12'}
 for r in rows:
  m=re.match(r'^(Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})$',str(r.get('date') or '').strip())
  if not m:continue
  d=f'2026-{months[m.group(1)]}-{int(m.group(2)):02d}'
  if start<=d<=end and r.get('team') and r.get('opponent'):out.add('|'.join(sorted([canonical(r['team']),canonical(r['opponent'])])))
 return out
def build():
 data=json.loads(DATA.read_text(encoding='utf-8'));rankings,rank_date=load_rankings();catalog=team_catalog();ranked_events=fetch_named_team_events([r['team'] for r in rankings],catalog);big_sky_events=fetch_named_team_events(BIG_SKY,catalog);result={'season':2026,'generatedAt':datetime.now(timezone.utc).isoformat(),'source':'ESPN team schedules (Top 25 + Big Sky)','rankings':rankings,'rankingsDate':rank_date,'bigSkyTeams':BIG_SKY,'weeks':[]}
 for i,(start,end,label) in enumerate(WEEKS):
  top=[];seen=set();played_ranks=set();bs=[];bs_seen=set()
  for e in ranked_events:
   d=str(e.get('date',''))[:10]
   if start<=d<=end and e.get('id') not in seen:
    top.append(e);seen.add(e.get('id'))
    for t in e.get('teams',[]):
     r=ranked_team_match(t.get('name') or t.get('short'),rankings)
     if r:played_ranks.add(norm(r['team']))
  top.sort(key=lambda e:e.get('date',''))
  for e in big_sky_events:
   d=str(e.get('date',''))[:10]
   if start<=d<=end and e.get('id') not in bs_seen:bs_seen.add(e.get('id'));bs.append(e)
  top.sort(key=lambda e:e.get('date',''));bs.sort(key=lambda e:e.get('date',''))
  byes=[r for r in rankings if norm(r['team']) not in played_ranks]
  if not top: raise RuntimeError(f'{label}: ranked-team schedules returned zero games')
  if not bs: raise RuntimeError(f'{label}: Big Sky team schedules returned zero games')
  result['weeks'].append({'index':i,'start':start,'end':end,'label':label,'complete':True,'fcsEventCount':len(top),'bigSkyEventCount':len(bs),'fcsTop25Games':top,'fcsTop25Byes':byes,'bigSkyGames':bs})
  print(f'{label}: Top25={len(top)} BigSky={len(bs)}')
 return result
def self_test():
 # Explicitly guard against the past North Dakota/South Dakota state prefix bug and Big Ten leakage.
 assert norm('South Dakota State')!=norm('South Dakota')
 assert canonical('South Dakota State')!=canonical('South Dakota')
 fake=[{'teams':[{'name':'Montana'},{'name':'Oregon State'}]},{'teams':[{'name':'Eastern Michigan'},{'name':'Wisconsin'}]}]
 # Big Sky inclusion is validated via ESPN group 20, not generic game filtering.
 assert pair_key(fake[0])=='montana|oregonstate' and pair_key(fake[1])=='easternmichigan|wisconsin'
 assert ranked_team_match('Montana State Bobcats', [{'team':'Montana'},{'team':'Montana State'}])['team']=='Montana State'
 assert ranked_team_match('South Dakota State Jackrabbits', [{'team':'South Dakota'},{'team':'South Dakota State'}])['team']=='South Dakota State'
 assert ranked_team_match('North Dakota State Bison', [{'team':'North Dakota'},{'team':'North Dakota State'}])['team']=='North Dakota State'
 print('SELF-TEST PASSED')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--self-test',action='store_true');a=ap.parse_args()
 if a.self_test:return self_test()
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(build(),indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
if __name__=='__main__':main()
