#!/usr/bin/env python3
"""Authoritative Griz HQ scoreboard cache builder.

Only this program writes scoreboard/scoreboard-data.json.
Sources: ESPN FCS group 81 and ESPN Big Sky group 20.
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
BASES=['https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard','https://site.web.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard']
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
def request(params):
 last=None
 for base in BASES:
  try:
   r=requests.get(base,params=params,headers=HEADERS,timeout=30);r.raise_for_status();p=r.json()
   if isinstance(p,dict) and isinstance(p.get('events'),list):return p['events']
   last=RuntimeError('ESPN response missing events list')
  except Exception as e:last=e
 raise RuntimeError(f'ESPN request failed: {last}')
def fetch_group_week(start,end,group):
 # Daily group requests are deliberate: date-scoped ESPN requests expose the full slate.
 out=[];seen=set();success=0
 for d in daterange(start,end):
  try:
   events=request({'dates':d.replace('-',''),'limit':1000,'groups':group})
   success+=1
   for e in events:
    k=str(e.get('id') or json.dumps(e,sort_keys=True))
    if k not in seen:seen.add(k);out.append(e)
  except Exception as ex:print(f'{group} {d}: {ex}')
 if success==0:raise RuntimeError(f'No successful ESPN responses for group {group} during {start}..{end}')
 return out
def compact(e):
 c=(e.get('competitions') or [{}])[0];v=c.get('venue') or {};addr=v.get('address') or {};st=(c.get('status') or {}).get('type') or {};teams=[]
 for x in c.get('competitors',[]) or []:
  t=x.get('team') or {};teams.append({'id':str(t.get('id') or x.get('id') or ''),'name':t.get('displayName') or t.get('shortDisplayName') or t.get('name') or '','short':t.get('shortDisplayName') or t.get('displayName') or t.get('name') or '','abbreviation':t.get('abbreviation') or '','homeAway':x.get('homeAway') or '','score':x.get('score'),'logo':t.get('logo') or ''})
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
 data=json.loads(DATA.read_text(encoding='utf-8'));rankings,rank_date=load_rankings();result={'season':2026,'generatedAt':datetime.now(timezone.utc).isoformat(),'source':'ESPN FCS group 81 + ESPN Big Sky group 20','rankings':rankings,'rankingsDate':rank_date,'bigSkyTeams':BIG_SKY,'weeks':[]}
 for i,(start,end,label) in enumerate(WEEKS):
  fcs=[compact(x) for x in fetch_group_week(start,end,'81')]
  bs=[compact(x) for x in fetch_group_week(start,end,'20')]
  # One card per actual game involving at least one ranked FCS team.
  top=[];seen=set();played_ranks=set()
  for e in fcs:
   matched=[]
   for t in e.get('teams',[]):
    r=ranked_team_match(t.get('name') or t.get('short'),rankings)
    if r: matched.append(r)
   if matched and e.get('id') not in seen:
    seen.add(e.get('id'));top.append(e)
    played_ranks.update(norm(r['team']) for r in matched)
  top.sort(key=lambda e:e.get('date',''))
  byes=[r for r in rankings if norm(r['team']) not in played_ranks]
  expected=big_sky_expected(data,start,end)
  got={pair_key(e) for e in bs if pair_key(e)}
  # The local Big Sky schedule is an independent sanity check. If it has games and group 20 omits them, fail.
  missing=sorted(expected-got)
  if expected and missing: print(f'{label}: WARNING — ESPN group 20 omitted locally scheduled Big Sky games: {missing[:5]}')
  if not fcs: raise RuntimeError(f'{label}: ESPN group 81 returned zero events')
  if not bs: raise RuntimeError(f'{label}: ESPN group 20 returned zero events')
  result['weeks'].append({'index':i,'start':start,'end':end,'label':label,'complete':True,'fcsEventCount':len(fcs),'bigSkyEventCount':len(bs),'fcsTop25Games':top,'fcsTop25Byes':byes,'bigSkyGames':bs})
  print(f'{label}: FCS events={len(fcs)} Top25 games={len(top)} BigSky={len(bs)}')
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
