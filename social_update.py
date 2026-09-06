import json, re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import requests
from bs4 import BeautifulSoup

UA='Mozilla/5.0 (compatible; GrizHQ/1.0; +https://grizhq.com/)'
HEADERS={'User-Agent':UA,'Accept-Language':'en-US,en;q=0.9'}
SOURCES=[
    ('Montana Griz Football','https://www.youtube.com/@MontanaGrizFootball/videos'),
    ('Skyline Sports','https://skylinesportsmt.com/skyline-sports-youtube/'),
]
BAD=re.compile(r'\b(montana state|montana st\.?|bobcats|bozeman)\b',re.I)

def clean(s): return re.sub(r'\s+',' ',BeautifulSoup(s or '','html.parser').get_text(' ',strip=True)).strip()

def yt_id(url):
    m=re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([A-Za-z0-9_-]{11})',url or '')
    return m.group(1) if m else ''

def add_yt(items, html, source):
    # Pull video IDs/titles from YouTube's server-rendered JSON and regular links.
    for m in re.finditer(r'"videoId":"([A-Za-z0-9_-]{11})".*?"title":\{"runs":\[\{"text":"(.*?)"',html):
        vid,title=m.group(1),m.group(2)
        title=bytes(title,'utf8').decode('unicode_escape','ignore')
        if BAD.search(title): continue
        items.append({'title':clean(title),'url':f'https://www.youtube.com/watch?v={vid}','image':f'https://i.ytimg.com/vi/{vid}/hqdefault.jpg','source':source,'type':'VIDEO','video':True,'description':'Montana Grizzlies video and short-form content.','date':datetime.now(timezone.utc).strftime('%B %-d, %Y')})
    # Fallback to links + nearby text.
    soup=BeautifulSoup(html,'html.parser')
    for a in soup.select('a[href*="/watch?v="],a[href*="/shorts/"]'):
        url=a.get('href',''); vid=yt_id(url)
        if not vid: continue
        title=clean(a.get_text(' ',strip=True))
        if not title or BAD.search(title) or any(x['url'].endswith(vid) for x in items): continue
        items.append({'title':title,'url':('https://www.youtube.com'+url if url.startswith('/') else url),'image':f'https://i.ytimg.com/vi/{vid}/hqdefault.jpg','source':source,'type':'VIDEO','video':True,'description':'Montana Grizzlies video and short-form content.','date':datetime.now(timezone.utc).strftime('%B %-d, %Y')})

def main():
    items=[]
    for source,url in SOURCES:
        try:
            r=requests.get(url,headers=HEADERS,timeout=20); r.raise_for_status(); add_yt(items,r.text,source)
        except Exception as e:
            print(f'Warning: {source}: {e}')
    # Dedupe and keep first 8. Add official social profile cards if feed is thin.
    seen=set(); out=[]
    for x in items:
        if x['url'] in seen: continue
        seen.add(x['url']); out.append(x)
    out=out[:8]
    if len(out)<4:
        out += [
          {'title':'Montana Griz Football on X','url':'https://x.com/MontanaGrizFB','image':'hero.jpg','source':'X','type':'FOLLOW','video':False,'description':'Official Montana Griz Football posts, news and game-day content.','date':'Official account'},
          {'title':'Montana Griz Football on Instagram','url':'https://www.instagram.com/montanagrizfootball/','image':'hero.jpg','source':'INSTAGRAM','type':'FOLLOW','video':False,'description':'Official Montana Griz Football photos, reels and team content.','date':'Official account'},
        ]
    payload={'updated':datetime.now(timezone.utc).isoformat(),'posts':out[:8]}
    with open('social.json','w',encoding='utf-8') as f: json.dump(payload,f,indent=2,ensure_ascii=False)

if __name__=='__main__': main()
