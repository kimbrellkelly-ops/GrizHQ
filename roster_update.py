#!/usr/bin/env python3
"""Surgical Griz HQ roster/coach updater.

Updates ONLY the dedicated Roster HQ data/coach markers in index.html.
- Roster data comes from the official GoGriz 2026 print roster.
- Player photos come from the actual official roster page image URLs; no filename guessing.
- Coaching staff comes from the official 2026 football staff page.
- If parsing/validation fails, index.html is left untouched.
This updater intentionally does NOT touch the scoreboard, news, social, stats,
schedule, transfer tracker, depth chart, or honors/watchlist content.
"""
from __future__ import annotations
import argparse, html, json, re, sys, urllib.parse, urllib.request
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
ROSTER_PRINT_URL = "https://gogriz.com/sports/football/roster/print"
ROSTER_PAGE_URL = "https://gogriz.com/sports/football/roster"
COACHES_URL = "https://gogriz.com/sports/football/coaches/2026"

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.in_tr=False; self.in_cell=False; self.rows=[]; self.row=[]; self.cell=[]
    def handle_starttag(self, tag, attrs):
        tag=tag.lower()
        if tag=='tr': self.in_tr=True; self.row=[]
        elif self.in_tr and tag in ('td','th'): self.in_cell=True; self.cell=[]
    def handle_endtag(self, tag):
        tag=tag.lower()
        if self.in_tr and tag in ('td','th') and self.in_cell:
            self.row.append(re.sub(r'\s+',' ',''.join(self.cell)).strip()); self.in_cell=False
        elif tag=='tr' and self.in_tr:
            if self.row: self.rows.append(self.row)
            self.in_tr=False
    def handle_data(self,data):
        if self.in_cell: self.cell.append(data)

class ImageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.images=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower()!='img': return
        d=dict(attrs); src=d.get('src') or d.get('data-src') or d.get('data-lazy-src') or ''
        if src: self.images.append({'src':src,'alt':d.get('alt',''),'title':d.get('title','')})

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.links=[]; self.href=''; self.text=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower()=='a': self.href=dict(attrs).get('href',''); self.text=[]
    def handle_endtag(self,tag):
        if tag.lower()=='a' and self.href:
            self.links.append((self.href,re.sub(r'\s+',' ',' '.join(self.text)).strip())); self.href=''; self.text=[]
    def handle_data(self,data):
        if self.href: self.text.append(data)

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'GrizHQ-RosterUpdater/2.0 (+fan project; official roster refresh)','Accept':'text/html,application/xhtml+xml'})
    with urllib.request.urlopen(req,timeout=45) as r: return r.read().decode('utf-8','replace')

def clean_height(v): return re.sub(r'\s+','',v.replace("''", "'"))
def clean_weight(v): return re.sub(r'\D+','',v or '')
def norm(s): return re.sub(r'[^a-z0-9]+','',(s or '').lower())

def parse_roster(page):
    p=TableParser(); p.feed(page); players=[]
    for row in p.rows:
        if len(row)<7: continue
        n,name,year,pos,ht,wt=row[:6]
        if not (re.fullmatch(r'\d+',n or '') or n.upper()=='TBD'): continue
        if not name or name.lower().startswith('retired in honor'): continue
        if not pos or not re.fullmatch(r'[A-Za-z/]+',pos): continue
        combined=row[6].strip() if len(row)>6 else ''
        explicit=row[7].strip() if len(row)>7 else ''
        if ' / ' in combined: home,listed=combined.split(' / ',1)
        else: home,listed=combined,''
        prev=explicit or listed
        players.append({'n':n,'name':name,'year':year,'pos':pos,'ht':clean_height(ht),'wt':clean_weight(wt),'home':home,'school':prev})
    return players

def validate_roster(players):
    if len(players)<90: raise RuntimeError(f'Safety stop: only {len(players)} roster players parsed')
    names=[p['name'] for p in players]; dup=[n for n,c in Counter(names).items() if c>1]
    if dup: raise RuntimeError('Safety stop: duplicate player names: '+', '.join(dup[:8]))
    required=["Keali'i Ah Yat","Eli Gillman","Peyton Wing","Jake Mason"]
    missing=[n for n in required if n not in names]
    if missing: raise RuntimeError('Safety stop: core players missing: '+', '.join(missing))
    for p in players:
        if not all(p.get(k) for k in ('name','year','pos','ht','wt')): raise RuntimeError(f"Safety stop: incomplete row {p.get('name')!r}")

def absolute_url(src,base): return urllib.parse.urljoin(base,src)
def valid_image_url(u):
    low=u.lower()
    return ('sidearm' in low or 'gogriz.com' in low or 'cloudfront.net' in low) and not low.startswith('data:')

def verified_photos(roster_page, players):
    ip=ImageParser(); ip.feed(roster_page)
    imgs=[]
    for x in ip.images:
        u=absolute_url(x['src'],ROSTER_PAGE_URL)
        if valid_image_url(u): imgs.append({'url':u,'alt':x['alt'],'title':x['title']})
    out={}
    for p in players:
        key=norm(p['name'])
        for im in imgs:
            if key and (norm(im['alt'])==key or norm(im['title'])==key or key in norm(im['alt']) or key in norm(im['title'])):
                out[p['name']]=im['url']; break
    for p in players:
        if p['name'] in out: continue
        idx=roster_page.lower().find(p['name'].lower())
        if idx<0: continue
        window=roster_page[max(0,idx-4500):idx+1500]
        candidates=re.findall(r'<img\b[^>]*(?:src|data-src|data-lazy-src)=["\']([^"\']+)["\'][^>]*>',window,re.I)
        for src in candidates:
            u=absolute_url(src,ROSTER_PAGE_URL)
            if valid_image_url(u): out[p['name']]=u; break
    return out

CORE_COACHES = [
    "Bobby Kennedy", "Brent Pease", "Rob Phenicie", "Eric Sanders",
    "Chris White", "Wes Nurse", "Dominic Daste", "Jaylen Johnson",
    "Kim McCloud", "Brent Myers", "Eric Price", "Nic Roger", "Dan Ryan"
]

def parse_coaches(page):
    p=TableParser(); p.feed(page); rows=[]
    wanted={norm(x):x for x in CORE_COACHES}
    for row in p.rows:
        if len(row)<2: continue
        name,title=row[0].strip(),row[1].strip()
        key=wanted.get(norm(name))
        if key and title: rows.append({'name':key,'title':title})
    by_name={x['name']:x for x in rows}
    return [by_name[n] for n in CORE_COACHES if n in by_name]

def validate_coaches(coaches):
    names={c['name'] for c in coaches}
    if 'Bobby Kennedy' not in names: raise RuntimeError('Safety stop: Bobby Kennedy not found on official coaches page')
    if 'Eric Sanders' not in names: raise RuntimeError('Safety stop: Eric Sanders not found on official coaches page')
    if len(coaches)<10: raise RuntimeError(f'Safety stop: only {len(coaches)} core coaches parsed')
    return coaches

def html_escape(s): return html.escape(str(s),quote=True)

def roster_raw(players):
    return '\n'.join('|'.join(str(p[k]).replace('|','/') for k in ('n','name','year','pos','ht','wt','home','school')) for p in players)

def coach_html(coaches, coach_photos):
    cards=[]
    for c in coaches:
        photo=coach_photos.get(c['name'],'')
        pic=f'<img src="{html_escape(photo)}" alt="{html_escape(c["name"])}" loading="lazy">' if photo else '<span class="griz-coach-photo-placeholder">M</span>'
        cards.append(f'<article class="griz-coach-card"><div class="griz-coach-photo">{pic}</div><div class="griz-coach-info"><span class="eyebrow">COACHING STAFF</span><h4>{html_escape(c["name"])}</h4><p>{html_escape(c["title"])}</p><a href="https://gogriz.com/sports/football/coaches/2026" target="_blank" rel="noopener">OFFICIAL STAFF PROFILE ↗</a></div></article>')
    return '\n'.join(cards)

def update_index(text,players,photos,coaches,coach_photos):
    a=text.find('const raw=`')
    if a<0: raise RuntimeError('Safety stop: roster raw marker missing')
    s=a+len('const raw=`'); e=text.find('`;\nconst roster=',s)
    if e<0: raise RuntimeError('Safety stop: roster raw end marker missing')
    text=text[:s]+roster_raw(players)+text[e:]

    ps=text.find('const rosterPhotos=')
    if ps<0: raise RuntimeError('Safety stop: roster photo marker missing')
    # The updater intentionally removes filename-guessing logic.  Older versions
    # expected a rosterPhotoBase marker here, but current index.html now has only
    # `};` followed directly by photoFor().  Locate the actual object terminator
    # instead of depending on a removed legacy marker.
    pe=text.find('};',ps)
    if pe<0: raise RuntimeError('Safety stop: roster photo map end marker missing')
    photo_js='const rosterPhotos='+json.dumps(photos,ensure_ascii=False,indent=2)+';'
    text=text[:ps]+photo_js+'\n'+text[pe+2:]
    # Disable filename guessing; photos are verified URLs only.
    text=re.sub(r"const rosterPhotoBase='[^']*';\nfunction generatedRosterPhoto\(p\)\{.*?\}\nfunction photoFor\(p\)\{return rosterPhotos\[p.name\]\|\|generatedRosterPhoto\(p\);\}","function photoFor(p){return rosterPhotos[p.name]||'';}",text,count=1,flags=re.S)
    # Also normalize an already-modern photoFor function without changing any other JS.
    text=re.sub(r"function photoFor\(p\)\{return rosterPhotos\[p\.name\]\|\|'';\}","function photoFor(p){return rosterPhotos[p.name]||'';}",text,count=1)

    start='<!-- ROSTER_COACHES_START -->'; end='<!-- ROSTER_COACHES_END -->'
    if start not in text or end not in text: raise RuntimeError('Safety stop: coach section markers missing')
    block=f'''{start}\n<section class="griz-coaches-section" id="roster-coaches">\n  <div class="griz-coaches-head"><div><div class="eyebrow">THE STAFF</div><h3>Coaching Staff</h3><p>The 2026 Montana football coaching staff, pulled from the official GoGriz staff page.</p></div><a class="button outline-maroon" href="{COACHES_URL}" target="_blank" rel="noopener">OFFICIAL STAFF ↗</a></div>\n  <div class="griz-coaches-grid">{coach_html(coaches,coach_photos)}</div>\n</section>\n{end}'''
    text=re.sub(re.escape(start)+r'.*?'+re.escape(end),lambda m:block,text,count=1,flags=re.S)

    def unit(pos):
        if pos in {'K','KP','LS','P'}: return 'special'
        if pos in {'QB','RB','WR','TE','OL','OT','ATH'}: return 'offense'
        return 'defense'
    def class_key(value):
        # Official GoGriz currently uses labels such as "Fr.", "So.",
        # "Jr.", "Sr.", "5th", and "Gr.". Normalize punctuation
        # and spacing so the count logic is resilient to presentation changes.
        v=re.sub(r'[^a-z0-9]+','',str(value or '').lower())
        return {
            'fr':'FRESHMEN', 'freshman':'FRESHMEN',
            'so':'SOPHOMORES', 'sophomore':'SOPHOMORES',
            'jr':'JUNIORS', 'junior':'JUNIORS',
            'sr':'SENIORS', 'senior':'SENIORS',
            '5th':'5TH YEAR', '5thyear':'5TH YEAR',
            'gr':'GRADUATE', 'graduate':'GRADUATE',
        }.get(v,'OTHER')
    class_counts=Counter(class_key(p['year']) for p in players)
    counts={
        'OFFENSE':sum(unit(p['pos'])=='offense' for p in players),
        'DEFENSE':sum(unit(p['pos'])=='defense' for p in players),
        'SPECIALISTS':sum(unit(p['pos'])=='special' for p in players),
        'FRESHMEN':class_counts['FRESHMEN'],
        'SOPHOMORES':class_counts['SOPHOMORES'],
        'JUNIORS':class_counts['JUNIORS'],
        'SENIORS':class_counts['SENIORS'],
        '5TH YEAR':class_counts['5TH YEAR'],
    }
    raw_class_counts=Counter(str(p.get('year') or '').strip() for p in players)
    print('Raw roster class labels:', dict(raw_class_counts))
    print('Normalized class counts:', {k: class_counts[k] for k in ('FRESHMEN','SOPHOMORES','JUNIORS','SENIORS','5TH YEAR','GRADUATE','OTHER')})
    required_classes=('FRESHMEN','SOPHOMORES','JUNIORS','SENIORS','5TH YEAR')
    missing_classes=[k for k in required_classes if class_counts[k] == 0]
    if missing_classes:
        raise RuntimeError('Safety stop: expected class counts are zero: '+', '.join(missing_classes))
    snapshot="""<div class="roster-snapshot-grid">
  <div class="roster-snapshot-card"><span>{OFFENSE}</span><strong>OFFENSE</strong><small>QB · RB · WR · TE · OL</small></div>
  <div class="roster-snapshot-card"><span>{DEFENSE}</span><strong>DEFENSE</strong><small>DL · LB · DB</small></div>
  <div class="roster-snapshot-card"><span>{SPECIALISTS}</span><strong>SPECIALISTS</strong><small>K · P/KP · LS</small></div>
  <div class="roster-snapshot-card"><span>{FRESHMEN}</span><strong>FRESHMEN</strong><small>First-year players</small></div>
  <div class="roster-snapshot-card"><span>{SOPHOMORES}</span><strong>SOPHOMORES</strong><small>Second-year players</small></div>
  <div class="roster-snapshot-card"><span>{JUNIORS}</span><strong>JUNIORS</strong><small>Third-year players</small></div>
  <div class="roster-snapshot-card"><span>{SENIORS}</span><strong>SENIORS</strong><small>Fourth-year players</small></div>
  <div class="roster-snapshot-card"><span>{FIFTH_YEAR}</span><strong>5TH YEAR</strong><small>Graduate / extra-eligibility veterans</small></div>
</div>""".format(**{**counts,'FIFTH_YEAR':counts['5TH YEAR']})
    snapshot_start=text.find('<div class="roster-snapshot-grid">')
    snapshot_end=text.find('<div class="roster-explorer"', snapshot_start)
    if snapshot_start < 0 or snapshot_end < 0:
        raise RuntimeError('Safety stop: roster snapshot markers missing')
    text=text[:snapshot_start]+snapshot+'\n'+text[snapshot_end:]
    text=re.sub(r'(class="roster-hq-stat"><b>)\d+(</b><span>PLAYERS</span>)',rf'\g<1>{len(players)}\g<2>',text,count=1)
    text=re.sub(r'(id="roster-count">)\d+ PLAYERS',rf'\g<1>{len(players)} PLAYERS',text,count=1)
    text=re.sub(r'(id="roster-filter-note">)Showing all \d+ players',rf'\g<1>Showing all {len(players)} players',text,count=1)
    if 'data-roster-jump="roster-coaches"' not in text:
        needle='<button type="button" class="roster-section-nav-btn" data-roster-jump="roster-transfers">'
        repl='<button type="button" class="roster-section-nav-btn" data-roster-jump="roster-coaches">🏈 <span>COACHES</span></button>\n  '+needle
        text=text.replace(needle,repl,1)
    text=re.sub(r'<div class="griz-transfer-note"><b>Data note:</b> This first version is a verified snapshot, not the automated weekly tracker yet\..*?</div>','',text,count=1,flags=re.S)
    return text

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--check',action='store_true'); args=ap.parse_args()
    roster_page=fetch(ROSTER_PAGE_URL); roster_print=fetch(ROSTER_PRINT_URL); coaches_page=fetch(COACHES_URL)
    players=parse_roster(roster_print); validate_roster(players)
    photos=verified_photos(roster_page,players)
    if len(photos)<max(70,int(len(players)*0.65)):
        raise RuntimeError(f'Safety stop: only {len(photos)} verified player photos found for {len(players)} players')
    raw_coaches=parse_coaches(coaches_page); coaches=validate_coaches(raw_coaches)
    linkp=LinkParser(); linkp.feed(coaches_page)
    profile_links={}
    for href,label in linkp.links:
        if '/sports/football/roster/coaches/' not in href: continue
        n=norm(label)
        for c in coaches:
            ck=norm(c['name'])
            if ck and ck in n:
                profile_links[c['name']]=absolute_url(href,COACHES_URL); break
    coach_photos={}
    for c in coaches:
        profile=profile_links.get(c['name'])
        if not profile: continue
        try:
            profile_page=fetch(profile)
        except Exception as exc:
            print(f'Coach photo warning: could not fetch {c["name"]} profile: {exc}'); continue
        key=norm(c['name'])
        lp=LinkParser(); lp.feed(profile_page)
        for href,label in lp.links:
            if not valid_image_url(absolute_url(href,profile)): continue
            low=norm(label)
            if low.startswith('image') and key and key in low:
                coach_photos[c['name']]=absolute_url(href,profile); break
        if c['name'] in coach_photos: continue
        ip=ImageParser(); ip.feed(profile_page)
        for im in ip.images:
            alt=norm(im['alt']); title=norm(im['title'])
            if key and (key==alt or key==title or key in alt or key in title):
                u=absolute_url(im['src'],profile)
                if valid_image_url(u): coach_photos[c['name']]=u; break
        if c['name'] in coach_photos: continue
        surname=norm(c['name'].split()[-1])
        for im in ip.images:
            u=absolute_url(im['src'],profile)
            if valid_image_url(u) and surname and surname in norm(u): coach_photos[c['name']]=u; break
    if len(coach_photos)<5: print(f'Warning: only {len(coach_photos)} coach photos verified; continuing with placeholders')
    print(f'Roster: {len(players)} players; verified photos: {len(photos)}; coaches: {len(coaches)}; coach photos: {len(coach_photos)}')
    current=INDEX.read_text(encoding='utf-8'); updated=update_index(current,players,photos,coaches,coach_photos)
    if updated==current: print('No roster/coach changes detected.'); return
    if args.check: print('Check mode: no files changed.'); return
    INDEX.write_text(updated,encoding='utf-8'); print('Updated index.html surgically.')

if __name__=='__main__':
    try: main()
    except Exception as e: print('ROSTER UPDATE FAILED:',e,file=sys.stderr); sys.exit(1)
