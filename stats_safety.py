import json
from pathlib import Path

DATA = Path('data.json')

# Last known complete official snapshot. This is used only when the upstream
# scraper returns an empty category, preventing a successful refresh from
# publishing a visibly broken Stats Central page.
FALLBACK = {
  'passing': [
    {'player': "Keali'i Ah Yat", 'line': '42-68 • 547 YDS • 4 TD • 1 INT', 'extra': 'Long: 85'},
    {'player': 'Luke Flowers', 'line': '0-0 • 0 YDS • 0 TD • 0 INT', 'extra': ''}
  ],
  'rushing': [
    {'player': 'Eli Gillman', 'line': '32 CAR • 181 YDS • 4 TD', 'extra': 'Avg: 5.7'},
    {'player': 'Dylan Paine', 'line': '15 CAR • 79 YDS • 1 TD', 'extra': 'Avg: 5.3'}
  ],
  'receiving': [
    {'player': 'Brooks Davis', 'line': '12 REC • 154 YDS • 1 TD', 'extra': 'Long: 33'},
    {'player': 'Lekeldrick Bridges', 'line': '8 REC • 110 YDS • 1 TD', 'extra': 'Long: 53'},
    {'player': 'Landon Ransom-Goelz', 'line': '7 REC • 115 YDS • 0 TD', 'extra': 'Long: 37'},
    {'player': 'Eli Gillman', 'line': '4 REC • 99 YDS • 2 TD', 'extra': 'Long: 85'}
  ],
  'tackles': [
    {'player': 'Sage Salopek', 'line': '11 TKL • 10 SOLO', 'extra': '1 AST'},
    {'player': 'Braeden Orlandi', 'line': '11 TKL • 5 SOLO', 'extra': '6 AST'},
    {'player': 'Tanner Huff', 'line': '11 TKL • 5 SOLO', 'extra': '6 AST'},
    {'player': 'Kade Cutler', 'line': '7 TKL • 4 SOLO', 'extra': '3 AST'}
  ],
  'pressure': [
    {'player': 'Peyton Wing', 'line': '1 TFL • 0 SACK • 0 FF', 'extra': '1 INT • 2 PBU'},
    {'player': 'Tyler King', 'line': '1.0 TFL • 1 SACK • 1 FF', 'extra': '10 sack yards'},
    {'player': 'Styles Goodman', 'line': '1 TFL • 0 SACK • 1 FF', 'extra': '1 TFL'}
  ],
  'special': [
    {'player': "Everett O'Donnell", 'line': '6 PUNTS • 275 YDS • 45.8 AVG', 'extra': 'Long: 68 • 2 inside 20'},
    {'player': 'Jo Silver', 'line': '1/3 FG', 'extra': ''}
  ]
}

obj = json.loads(DATA.read_text(encoding='utf-8'))
stats = obj.setdefault('stats', {})
leaders = stats.setdefault('leaders', {})
changed = False
for key, rows in FALLBACK.items():
    current = leaders.get(key)
    if not isinstance(current, list) or not current or not any(isinstance(x, dict) and x.get('player') for x in current):
        leaders[key] = rows
        changed = True
if changed:
    DATA.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Stats safety fallback restored one or more empty leader categories.')
else:
    print('Stats leader categories are populated; no fallback needed.')
