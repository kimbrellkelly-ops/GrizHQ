import json, re
from pathlib import Path
import requests
from bs4 import BeautifulSoup

DATA=Path('data.json')
URL='https://gogriz.com/sports/football/stats/2026'
HEADERS={'User-Agent':'Mozilla/5.0 (compatible; GrizHQ/1.0; +https://grizhq.com)'}
BAD={'player','players','total','team','team totals','opponents','opponent','montana','individual','individual statistics'}

def clean(s): return re.sub(r'\s+',' ',s or '').strip()
def first_index(headers,*names):
    for name in names:
        for i,h in enumerate(headers):
            if h==name or h.startswith(name+' '): return i
    return None

def category_for(table):
    text=clean(' '.join([table.get('aria-label',''),table.get_text(' ',strip=True)[:500]])).lower()
    node=table
    for _ in range(8):
        node=node.find_previous(['h1','h2','h3','h4','h5','h6','caption','strong'])
        if not node: break
        text += ' '+clean(node.get_text(' ',strip=True)).lower()
    if 'passing' in text or ('cmp' in text and 'att' in text): return 'passing'
    if 'receiving' in text or 'receptions' in text or ('yds' in text and 'long' in text and 'no' in text): return 'receiving'
    if 'rushing' in text or ('gain' in text and 'loss' in text and 'att' in text): return 'rushing'
    if 'tackles' in text or ('solo' in text and ('ast' in text or 'assist' in text)): return 'tackles'
    if any(x in text for x in ('sacks','tfl','forced fumbles','passes defended')): return 'pressure'
    if any(x in text for x in ('punting','punts','field goals','kicking')): return 'special'
    return None

def parse_table(table,cat):
    trs=table.find_all('tr')
    if not trs: return []
    headers=[clean(x.get_text(' ',strip=True)).upper() for x in trs[0].find_all(['th','td'])]
    if len(headers)<3: return []
    name_i=first_index(headers,'PLAYER','NAME')
    if name_i is None: name_i=0
    def v(row,*names):
        i=first_index(headers,*names)
        return row[i] if i is not None and i<len(row) else ''
    out=[]
    for tr in trs[1:]:
        cells=[clean(x.get_text(' ',strip=True)) for x in tr.find_all(['td','th'])]
        if len(cells)<=name_i: continue
        name=cells[name_i]
        if name.lower() in BAD or len(name.split())<2 or not re.search('[A-Za-z]',name): continue
        if cat=='passing':
            comp=v(cells,'C-A','CMP-ATT','COMP-ATT','COMP'); y=v(cells,'YDS','YARD'); td=v(cells,'TD'); inte=v(cells,'INT'); lg=v(cells,'LONG')
            line=f'{comp or "0"} • {y or "0"} YDS • {td or "0"} TD • {inte or "0"} INT'; extra=f'Long: {lg}' if lg else ''
        elif cat=='rushing':
            att=v(cells,'ATT','CAR'); y=v(cells,'YDS','YARD','NET'); td=v(cells,'TD'); avg=v(cells,'AVG'); lg=v(cells,'LONG')
            line=f'{att or "0"} CAR • {y or "0"} YDS • {td or "0"} TD'; extra=f'Avg: {avg}' if avg else (f'Long: {lg}' if lg else '')
        elif cat=='receiving':
            rec=v(cells,'REC','RECEPTIONS','NO'); y=v(cells,'YDS','YARD'); td=v(cells,'TD'); lg=v(cells,'LONG')
            line=f'{rec or "0"} REC • {y or "0"} YDS • {td or "0"} TD'; extra=f'Long: {lg}' if lg else ''
        elif cat=='tackles':
            total=v(cells,'TOT','TKL','TOTAL'); solo=v(cells,'SOLO'); ast=v(cells,'AST','ASSIST')
            line=f'{total or "0"} TKL • {solo or "0"} SOLO'; extra=f'{ast or "0"} AST'
        elif cat=='pressure':
            tfl=v(cells,'TFL'); sack=v(cells,'SACK','SACKS'); ff=v(cells,'FF'); inte=v(cells,'INT'); pbu=v(cells,'PBU')
            line=f'{tfl or "0"} TFL • {sack or "0"} SACK • {ff or "0"} FF'; extra=f'{inte or "0"} INT • {pbu or "0"} PBU'
        elif cat=='special':
            punts=v(cells,'PUNTS','PUNT'); y=v(cells,'YDS','YARD'); avg=v(cells,'AVG'); lg=v(cells,'LONG'); in20=v(cells,'IN20','INSIDE 20','I20')
            fgm=v(cells,'FGM','MADE'); fga=v(cells,'FGA','ATT')
            if punts:
                line=f'{punts} PUNTS • {y or "0"} YDS • {avg or "0"} AVG'
                extra=' • '.join(x for x in [f'Long: {lg}' if lg else '',f'{in20} inside 20' if in20 else ''] if x)
            elif fgm or fga:
                line=f'{fgm or "0"}/{fga or "0"} FG'; extra=''
            else:
                continue
        else: continue
        out.append({'player':name,'line':line,'extra':extra})
    return out[:5]

def main():
    data=json.loads(DATA.read_text(encoding='utf-8'))
    r=requests.get(URL,headers=HEADERS,timeout=45); r.raise_for_status()
    soup=BeautifulSoup(r.text,'html.parser')
    leaders={k:[] for k in ('passing','rushing','receiving','tackles','pressure','special')}
    for table in soup.find_all('table'):
        cat=category_for(table)
        if not cat: continue
        parsed=parse_table(table,cat)
        if not parsed: continue
        if cat=='special':
            leaders[cat].extend(parsed)
            leaders[cat]=leaders[cat][:5]
        elif not leaders[cat]:
            leaders[cat]=parsed
    found=[k for k,v in leaders.items() if v]
    if not found: raise RuntimeError('No official player-stat tables detected')
    stats=data.setdefault('stats',{})
    stats['leaders']=leaders
    stats['leaders_source']=URL
    stats['leaders_updated']=data.get('updated')
    DATA.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Refreshed official player stats:',', '.join(found))
if __name__=='__main__': main()
