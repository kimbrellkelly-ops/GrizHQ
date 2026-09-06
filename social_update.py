import json, re
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup

UA='Mozilla/5.0 (compatible; GrizHQ/1.0; +https://grizhq.com/)'
HEADERS={'User-Agent':UA,'Accept-Language':'en-US,en;q=0.9'}
BAD=re.compile(r'\b(montana state|montana st\.?|bobcats|bozeman|cat-griz)\b',re.I)
YT_IMG_RE=re.compile(r'i\.ytimg\.com/vi/([A-Za-z0-9_-]{11})/',re.I)

SKYLINE_YOUTUBE='https://skylinesportsmt.com/skyline-sports-youtube/'
SKYLINE_PROFILE='https://www.youtube.com/@skylinesports'
X_PROFILE='https://x.com/MontanaGrizFB'
INSTAGRAM_PROFILE='https://www.instagram.com/montanagrizfootball/'


def clean(s):
    return re.sub(r'\s+',' ',BeautifulSoup(s or '','html.parser').get_text(' ',strip=True)).strip()


def parse_date(text):
    m=re.search(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b', text or '')
    return m.group(0) if m else 'Recent'


def parse_skyline_youtube():
    """Read Skyline's public video list via its actual YouTube thumbnail links.
    The page exposes i.ytimg.com/vi/<ID>/... image links, so we can reliably
    recover the YouTube video ID even when watch links are not in the HTML.
    """
    try:
        r=requests.get(SKYLINE_YOUTUBE,headers=HEADERS,timeout=20)
        r.raise_for_status()
        soup=BeautifulSoup(r.text,'html.parser')
    except Exception as e:
        print('Skyline YouTube warning:',e)
        return []

    out=[]; seen=set()
    for img in soup.find_all('img'):
        src=' '.join([img.get('src') or '',img.get('data-src') or '',img.get('data-original') or ''])
        m=YT_IMG_RE.search(src)
        if not m: continue
        vid=m.group(1)
        if vid in seen: continue

        # Walk upward until we find a compact card-like text block.
        node=img
        best=''
        for _ in range(5):
            node=node.parent if node else None
            if not node: break
            txt=clean(node.get_text(' ',strip=True))
            if 10 <= len(txt) <= 500:
                best=txt
        if not best: continue

        # Remove dates/durations from the title area when possible.
        title=best
        title=re.sub(r'\b\d{1,2}:\d{2}(?::\d{2})?\b','',title)
        title=re.sub(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b','',title)
        title=clean(title)
        if not title or BAD.search(title): continue
        if not re.search(r'\b(griz|montana|gillman|bobby kennedy|grizzlies|southern utah|suu)\b',title,re.I): continue

        # Only keep Montana-related Skyline videos; exclude mixed/general items.
        out.append({
            'title': title[:180],
            'url': f'https://www.youtube.com/watch?v={vid}',
            'image': f'https://i.ytimg.com/vi/{vid}/hqdefault.jpg',
            'source':'Skyline Sports YouTube',
            'type':'YOUTUBE',
            'video':True,
            'description':'Montana Griz video from the Skyline Sports YouTube channel.',
            'date':parse_date(best),
            'platform':'youtube',
            'youtube_id':vid
        })
        seen.add(vid)
        if len(out)>=8: break
    return out


def main():
    videos=parse_skyline_youtube()
    # Keep the official social profiles visible even when an X/Instagram
    # post cannot be fetched reliably by a GitHub Action.
    payload={
        'updated':datetime.now(timezone.utc).isoformat(),
        'posts':videos[:8],
        'profiles':[
            {'name':'Montana Griz Football on X','url':X_PROFILE},
            {'name':'Montana Griz Football on Instagram','url':INSTAGRAM_PROFILE},
            {'name':'Skyline Sports YouTube','url':SKYLINE_PROFILE}
        ]
    }
    with open('social.json','w',encoding='utf-8') as f:
        json.dump(payload,f,indent=2,ensure_ascii=False)
    print(f'Wrote {len(videos[:8])} verified Griz social/video cards')

if __name__=='__main__': main()
