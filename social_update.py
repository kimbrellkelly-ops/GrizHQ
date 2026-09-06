import json, re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import requests
from bs4 import BeautifulSoup

UA='Mozilla/5.0 (compatible; GrizHQ/1.0; +https://grizhq.com/)'
HEADERS={'User-Agent':UA,'Accept-Language':'en-US,en;q=0.9'}
BAD=re.compile(r'\b(montana state|montana st\.?|bobcats|bozeman)\b',re.I)

# Verified Griz-focused pages. These are deliberately curated so the cards never
# point to dead/placeholder YouTube URLs. Images are pulled from each page's
# actual og:image/twitter/schema image when available.
SOURCES=[
 ('Skyline Sports','WATCH – Griz press conference – Bobby Kennedy, Eli Gillman & Tyler King + Drake’s Matt Walker','https://skylinesportsmt.com/watch-griz-press-conference-bobby-kennedy-eli-gillman-tyler-king-drakes-matt-walker/'),
 ('Skyline Sports','Gillman breaks record as Griz overcome penalties to cruise past Drake for second straight win','https://skylinesportsmt.com/gillman-breaks-record-as-griz-overcome-penalties-to-cruise-past-drake-for-second-straight-win/'),
 ('Skyline Sports','Talkin’ Schmidt – Andrew give top 3 Griz players from season-opening + best/worst of BK debut','https://skylinesportsmt.com/talkin-schmidt-andrew-give-top-3-griz-players-from-season-opening-best-worst-of-bk-debut/'),
 ('Skyline Sports','Nuanez brothers on Big Sky opening weekend, Montana escaping against Southern Utah','https://skylinesportsmt.com/nuanez-brothers-on-big-sky-opening-weekend-montana-escaping-against-southern-utah/'),
 ('GoGriz','Gillman sets records as Griz roll past Bulldogs 45-10','https://gogriz.com/news/2026/9/5/football-gillman-sets-records-as-griz-roll-past-bulldogs-45-10'),
 ('Daily Inter Lake','Give Gillman the crown: Griz ride RBs 4 touchdowns to win over Drake','https://dailyinterlake.com/news/2026/sep/06/give-gillman-the-crown-griz-ride-rbs-4-touchdowns-to-win-pver-drake/'),
]

def clean(s):
 return re.sub(r'\s+',' ',BeautifulSoup(s or '','html.parser').get_text(' ',strip=True)).strip()

def parse_date(value):
 if not value: return ''
 value=value.strip()
 try:
  return parsedate_to_datetime(value).astimezone(timezone.utc).strftime('%B %-d, %Y')
 except Exception: pass
 for fmt in ('%Y-%m-%dT%H:%M:%S%z','%Y-%m-%dT%H:%M:%S.%f%z','%Y-%m-%d','%B %d, %Y'):
  try: return datetime.strptime(value,fmt).strftime('%B %-d, %Y')
  except Exception: pass
 return ''

def meta(soup,*names):
 for name in names:
  tag=soup.find('meta',attrs={'property':name}) or soup.find('meta',attrs={'name':name})
  if tag and tag.get('content'): return tag['content'].strip()
 return ''

def fetch(item):
 source,title,url=item
 try:
  r=requests.get(url,headers=HEADERS,timeout=20)
  r.raise_for_status()
  soup=BeautifulSoup(r.text,'html.parser')
  real_title=meta(soup,'og:title','twitter:title') or (soup.title.get_text(' ',strip=True) if soup.title else title)
  image=meta(soup,'og:image','twitter:image','twitter:image:src')
  if not image:
   for img in soup.select('article img, main img, img'):
    candidate=img.get('src') or img.get('data-src') or img.get('data-lazy-src')
    if candidate and candidate.startswith(('http://','https://')):
     image=candidate; break
  date=meta(soup,'article:published_time','datePublished','date')
  if not date:
   t=soup.find('time')
   date=t.get('datetime','') if t else ''
  date=parse_date(date)
  text=clean(soup.get_text(' ',strip=True))[:4000]
  video=bool(soup.select_one('iframe[src*="youtube"], iframe[src*="youtu.be"], video')) or bool(re.search(r'\b(video|watch|press conference|podcast)\b', real_title, re.I))
  if BAD.search(real_title) or BAD.search(text[:1500]): return None
  return {'title':clean(real_title).replace(' – Skyline Sports','').strip() or title,
          'url':url,'image':image or 'hero.jpg','source':source,
          'type':'VIDEO' if video else 'SOCIAL','video':video,
          'description':('Griz video and media content from a verified Montana football source.' if video else 'Montana football social and media highlight from a verified source.'),
          'date':date or 'Recent'}
 except Exception as e:
  print(f'Warning: {url}: {e}')
  return None

def main():
 out=[]; seen=set()
 for item in SOURCES:
  x=fetch(item)
  if x and x['url'] not in seen:
   seen.add(x['url']); out.append(x)
 payload={'updated':datetime.now(timezone.utc).isoformat(),'posts':out[:6],
          'profiles':[
            {'name':'Montana Griz Football on X','url':'https://x.com/MontanaGrizFB'},
            {'name':'Montana Griz Football on Instagram','url':'https://www.instagram.com/montanagrizfootball/'}
          ]}
 with open('social.json','w',encoding='utf-8') as f: json.dump(payload,f,indent=2,ensure_ascii=False)
 print(f'Wrote {len(out)} verified Griz social/video cards')

if __name__=='__main__': main()
