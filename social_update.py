import json, re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import requests
from bs4 import BeautifulSoup

UA='Mozilla/5.0 (compatible; GrizHQ/1.0; +https://grizhq.com/)'
HEADERS={'User-Agent':UA,'Accept-Language':'en-US,en;q=0.9'}
BAD=re.compile(r'\b(montana state|montana st\.?|bobcats|bozeman)\b',re.I)
YT_RE=re.compile(r'(?:youtube(?:-nocookie)?\.com/(?:embed/|watch\?v=|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})',re.I)

# Real social sources only. No Griz HQ news/article URLs are used here.
X_PROFILE='https://x.com/MontanaGrizFB'
X_MIRROR='https://twstalker.com/MontanaGrizFB'
SKYLINE_YOUTUBE='https://skylinesportsmt.com/skyline-sports-youtube/'
SKYLINE_PROFILE='https://www.youtube.com/@skylinesports'


def clean(s):
    return re.sub(r'\s+',' ',BeautifulSoup(s or '','html.parser').get_text(' ',strip=True)).strip()


def parse_date(value):
    if not value: return ''
    value=value.strip()
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc).strftime('%b %-d, %Y')
    except Exception: pass
    for fmt in ('%Y-%m-%dT%H:%M:%S%z','%Y-%m-%dT%H:%M:%S.%f%z','%Y-%m-%d','%B %d, %Y'):
        try: return datetime.strptime(value,fmt).strftime('%b %-d, %Y')
        except Exception: pass
    return ''


def image_from_node(node):
    for img in node.find_all('img') if node else []:
        for key in ('src','data-src','data-original','data-lazy-src'):
            v=img.get(key)
            if v and v.startswith(('http://','https://')):
                if 'avatar' not in v.lower() and 'logo' not in v.lower(): return v
    return ''


def extract_youtube_id(url):
    m=YT_RE.search(url or '')
    return m.group(1) if m else ''


def youtube_thumb(vid):
    return f'https://i.ytimg.com/vi/{vid}/hqdefault.jpg' if vid else ''


def parse_x_posts():
    """Read the current public X mirror for the official @MontanaGrizFB account.
    This gives us actual social-post text instead of converting news articles into cards.
    """
    try:
        r=requests.get(X_MIRROR,headers=HEADERS,timeout=20)
        r.raise_for_status()
        soup=BeautifulSoup(r.text,'html.parser')
    except Exception as e:
        print('X mirror warning:',e)
        return []

    posts=[]
    seen=set()
    # TwStalker has changed markup over time, so use several broad selectors.
    nodes=soup.select('[class*="tweet"], [class*="status"], article')
    if not nodes:
        nodes=soup.find_all('div')
    for node in nodes:
        text=clean(node.get_text(' ',strip=True))
        if len(text)<25 or len(text)>700: continue
        if 'Montana Griz Football' not in text and '@MontanaGrizFB' not in text and '#GoGriz' not in text: continue
        if BAD.search(text): continue
        # Remove obvious profile/navigation text.
        if text in seen: continue
        seen.add(text)
        img=image_from_node(node)
        # Try to find a timestamp.
        dt=''
        t=node.find('time')
        if t: dt=parse_date(t.get('datetime') or t.get_text(' ',strip=True))
        posts.append({
            'title': text[:180] + ('…' if len(text)>180 else ''),
            'url': X_PROFILE,
            'image': img,
            'source':'@MontanaGrizFB • X',
            'type':'X POST',
            'video': bool(node.find('video')) or bool(node.select_one('[class*="video"]')),
            'description': text,
            'date': dt or 'Recent',
            'platform':'x'
        })
        if len(posts)>=6: break
    return posts


def parse_skyline_youtube():
    """Scrape Skyline's public YouTube listing and keep only Montana/Griz videos."""
    try:
        r=requests.get(SKYLINE_YOUTUBE,headers=HEADERS,timeout=20)
        r.raise_for_status()
        soup=BeautifulSoup(r.text,'html.parser')
    except Exception as e:
        print('Skyline YouTube warning:',e)
        return []

    out=[]; seen=set()
    # Collect YouTube IDs from embeds/links and use surrounding card text for titles.
    for tag in soup.find_all(['iframe','a','div','article']):
        href=tag.get('src') or tag.get('href') or ''
        vid=extract_youtube_id(href)
        if not vid: continue
        if vid in seen: continue
        parent=tag
        best=''
        for _ in range(4):
            if not parent: break
            txt=clean(parent.get_text(' ',strip=True))
            if 10 <= len(txt) <= 400:
                best=txt
            parent=parent.parent
        if not best: best=tag.get('title') or tag.get('aria-label') or ''
        if not best: continue
        if BAD.search(best): continue
        # Keep content that clearly references Montana/Griz or is on a Griz-focused item.
        if not re.search(r'\b(griz|montana|gillman|bobby kennedy|grizzlies)\b',best,re.I): continue
        out.append({
            'title':best[:180],
            'url':f'https://www.youtube.com/watch?v={vid}',
            'image':youtube_thumb(vid),
            'source':'Skyline Sports YouTube',
            'type':'YOUTUBE',
            'video':True,
            'description':'Montana Griz video from the Skyline Sports YouTube channel.',
            'date':'Recent',
            'platform':'youtube',
            'youtube_id':vid
        })
        seen.add(vid)
        if len(out)>=6: break
    return out


def main():
    posts=parse_x_posts()
    videos=parse_skyline_youtube()
    # Prefer a mix: current official X posts first, then real YouTube videos.
    combined=[]
    for item in posts[:4] + videos[:4]:
        if not any(x.get('url')==item.get('url') and x.get('title')==item.get('title') for x in combined):
            combined.append(item)
    payload={
        'updated':datetime.now(timezone.utc).isoformat(),
        'posts':combined[:8],
        'profiles':[
            {'name':'Montana Griz Football on X','url':X_PROFILE},
            {'name':'Montana Griz Football on Instagram','url':'https://www.instagram.com/montanagrizfootball/'},
            {'name':'Skyline Sports YouTube','url':SKYLINE_PROFILE}
        ]
    }
    with open('social.json','w',encoding='utf-8') as f:
        json.dump(payload,f,indent=2,ensure_ascii=False)
    print(f'Wrote {len(combined)} actual social/video cards')

if __name__=='__main__': main()
