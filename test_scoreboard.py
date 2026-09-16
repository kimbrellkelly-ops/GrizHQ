import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from refresh_scoreboards import load_rankings, canonical, validate_big_sky, validate_fcs, compact

rankings=load_rankings()
assert len(rankings)==25
assert canonical('South Dakota State') != canonical('South Dakota')
sample_raw={
  'id':'1001','date':'2026-09-19T19:00:00Z','name':'Eastern Michigan Eagles at Wisconsin Badgers','shortName':'EMU @ WISC',
  'competitions':[{'competitors':[
    {'homeAway':'home','team':{'id':'275','displayName':'Wisconsin Badgers','shortDisplayName':'Wisconsin','abbreviation':'WISC','logo':'https://a.espncdn.com/wisc.png'},'score':'0'},
    {'homeAway':'away','team':{'id':'2199','displayName':'Eastern Michigan Eagles','shortDisplayName':'Eastern Michigan','abbreviation':'EMU','logo':'https://a.espncdn.com/emu.png'},'score':'0'}
  ],'status':{'type':{'state':'pre','completed':False}}}]}
# This is deliberately NOT a Big Sky event and must fail the Big Sky source guard.
try:
    validate_big_sky([compact(sample_raw)])
except RuntimeError:
    pass
else:
    raise AssertionError('Unrelated FBS game passed Big Sky validation')
validate_fcs([compact(sample_raw)])
print('TEST SCOREBOARD PASSED')
print('25 rankings loaded; South Dakota/South Dakota State separated; Big Sky guard rejects unrelated FBS game.')
