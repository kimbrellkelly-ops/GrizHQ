import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

OUT = Path('social.json')
HEADERS = {'User-Agent':'GrizHQ-SocialBot/1.0 (+https://grizhq.com)'}

# Resolve public YouTube handles at runtime, then use YouTube's public Atom feed.
# This avoids an API key and keeps the social rail fresh with actual video posts.
CHANNEL_HANDLES = [
    ('Skyline Sports YouTube','https://www.youtube.com/@skylinesports','MONTANA|GRIZ|BIG SKY|FCS|SOUTHERN UTAH|DRAKE|UTAH TECH|IDAHO|MONTANA STATE'),
    ('Montana Griz Football YouTube','https://www.youtube.com/@MontanaGrizFB','MONTANA|GRIZ|FOOTBALL'),
    ('Big Sky Conference YouTube','https://www.youtube.com/@BigSkyConf','BIG SKY|MONTANA|GRIZ|FCS|FOOTBALL'),
]

VIDEO_RE = re.compile(r'(?:youtube(?:-nocookie)?\.com/(?:embed/|watch\?v=|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})', re.I)

def clean(v):
    return re.sub(r'\s+',' ',str(v or '')).strip()

def resolve_channel_id(handle_url):
    try:
        r=requests.get(handle_url,headers=HEADERS,timeout=20)
        r.raise_for_status()
        text=r.text
        patterns=[r'"channelId":"(UC[A-Za-z0-9_-]+)"',r'"externalId":"(UC[A-Za-z0-9_-]+)"',r'/channel/(UC[A-Za-z0-9_-]+)']
        for pat in patterns:
            m=re.search(pat,text)
            if m:return m.group(1)
    except Exception as e:
        print('channel resolve failed',handle_url,e)
    return ''

def parse_atom(source,feed_url,keyword_pattern):
    try:
        r=requests.get(feed_url,headers=HEADERS,timeout=20)
        r.raise_for_status()
        root=ET.fromstring(r.content)
    except Exception as e:
        print('feed failed',source,e); return []
    out=[]
    ns='{http://www.w3.org/2005/Atom}'
    for entry in root.findall(f'.//{ns}entry')[:25]:
        title=clean(entry.findtext(f'{ns}title'))
        link_node=entry.find(f'{ns}link')
        url=clean(link_node.attrib.get('href','') if link_node is not None else '')
        published=clean(entry.findtext(f'{ns}published') or entry.findtext(f'{ns}updated'))
        vid=clean(entry.findtext('{http://www.youtube.com/xml/schemas/2015}videoId'))
        if not vid:
            m=VIDEO_RE.search(url); vid=m.group(1) if m else ''
        if not title or not url: continue
        if keyword_pattern and not re.search(keyword_pattern,title,re.I): continue
        date=''
        try:
            dt=datetime.fromisoformat(published.replace('Z','+00:00')).astimezone(timezone.utc)
            date=dt.strftime('%b. %-d, %Y')
        except Exception: date=published[:10]
        out.append({
            'title':title,'url':url,'image':f'https://i.ytimg.com/vi/{vid}/hqdefault.jpg' if vid else '',
            'source':source,'type':'YOUTUBE','video':True,
            'description':f'{source} video update.','date':date,'platform':'youtube','youtube_id':vid,
            'published_at':published
        })
    return out

def load_existing():
    try:
        d=json.loads(OUT.read_text(encoding='utf-8'))
        return d.get('posts',[]) if isinstance(d,dict) else []
    except Exception:return []

def main():
    posts=[]
    for source,handle,pattern in CHANNEL_HANDLES:
        cid=resolve_channel_id(handle)
        if not cid:
            print('No channel id for',source); continue
        feed=f'https://www.youtube.com/feeds/videos.xml?channel_id={cid}'
        posts.extend(parse_atom(source,feed,pattern))
    # Preserve any manually/previously collected social items so a temporary
    # YouTube failure never blanks the rail.
    posts.extend(load_existing())
    by={}
    for p in posts:
        url=clean(p.get('url'))
        if not url or not p.get('title'): continue
        by[url]=p
    items=list(by.values())
    def key(x):
        try:return datetime.fromisoformat(str(x.get('published_at','')).replace('Z','+00:00')).timestamp()
        except:return 0
    items.sort(key=key,reverse=True)
    payload={'updated':datetime.now(timezone.utc).isoformat(),'posts':items[:30],
             'profiles':[
               {'name':'Montana Griz Football on X','url':'https://x.com/MontanaGrizFB'},
               {'name':'Montana Griz Football on Instagram','url':'https://www.instagram.com/montanagrizfootball/'},
               {'name':'Skyline Sports YouTube','url':'https://www.youtube.com/@skylinesports'},
               {'name':'Big Sky Conference YouTube','url':'https://www.youtube.com/@BigSkyConf'},
             ]}
    OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Wrote',len(payload['posts']),'social items')

if __name__=='__main__': main()
