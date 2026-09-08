import json
import re
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

OUT = Path('social.json')
HEADERS = {'User-Agent':'Mozilla/5.0 (compatible; GrizHQ-SocialBot/1.0; +https://grizhq.com)'}

# Public, no-key feeds. YouTube gives us actual video posts; X's public
# syndication endpoint gives us recent posts from public accounts.
YOUTUBE_CHANNELS = [
    ('Skyline Sports YouTube','https://www.youtube.com/@skylinesports','MONTANA|GRIZ|BIG SKY|FCS|SOUTHERN UTAH|DRAKE|UTAH TECH|IDAHO|MONTANA STATE'),
    ('Montana Griz Football YouTube','https://www.youtube.com/@MontanaGrizFB','MONTANA|GRIZ|FOOTBALL'),
    ('Big Sky Conference YouTube','https://www.youtube.com/@BigSkyConf','BIG SKY|MONTANA|GRIZ|FCS|FOOTBALL'),
]

X_ACCOUNTS = [
    ('Montana Griz Football X','MontanaGrizFB','MONTANA|GRIZ|FOOTBALL|GILLMAN|KENNEDY|GO GRIZ|#GRIZ'),
    ('Montana Grizzlies X','UMGRIZZLIES','MONTANA|GRIZ|FOOTBALL|GILLMAN|KENNEDY|GO GRIZ|#GRIZ'),
    ('Skyline Sports X','SkylineSportsMT','MONTANA|GRIZ|BIG SKY|FCS|DRAKE|UTAH TECH'),
    ('Big Sky Football X','BigSkyFB','BIG SKY|MONTANA|GRIZ|FCS|FOOTBALL'),
]

VIDEO_RE = re.compile(r'(?:youtube(?:-nocookie)?\.com/(?:embed/|watch\?v=|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})', re.I)


def clean(v):
    return re.sub(r'\s+', ' ', str(v or '')).strip()


def parse_date(value):
    value = clean(value)
    if not value:
        return None
    candidates = [
        value.replace('Z', '+00:00'),
        value,
    ]
    for candidate in candidates:
        try:
            dt = datetime.fromisoformat(candidate)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass
    for fmt in ('%a %b %d %H:%M:%S %z %Y', '%Y-%m-%d %H:%M:%S %z'):
        try:
            return datetime.strptime(value, fmt).astimezone(timezone.utc)
        except Exception:
            pass
    return None


def format_date(dt):
    return dt.strftime('%b. %-d, %Y') if dt else ''


def resolve_channel_id(handle_url):
    try:
        r = requests.get(handle_url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        text = r.text
        for pat in [r'"channelId":"(UC[A-Za-z0-9_-]+)"', r'"externalId":"(UC[A-Za-z0-9_-]+)"', r'/channel/(UC[A-Za-z0-9_-]+)']:
            m = re.search(pat, text)
            if m:
                return m.group(1)
    except Exception as e:
        print('channel resolve failed', handle_url, e)
    return ''


def parse_atom(source, feed_url, keyword_pattern):
    try:
        r = requests.get(feed_url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception as e:
        print('YouTube feed failed', source, e)
        return []
    out = []
    ns = '{http://www.w3.org/2005/Atom}'
    for entry in root.findall(f'.//{ns}entry')[:25]:
        title = clean(entry.findtext(f'{ns}title'))
        link_node = entry.find(f'{ns}link')
        url = clean(link_node.attrib.get('href', '') if link_node is not None else '')
        published = clean(entry.findtext(f'{ns}published') or entry.findtext(f'{ns}updated'))
        vid = clean(entry.findtext('{http://www.youtube.com/xml/schemas/2015}videoId'))
        if not vid:
            m = VIDEO_RE.search(url)
            vid = m.group(1) if m else ''
        if not title or not url:
            continue
        if keyword_pattern and not re.search(keyword_pattern, title, re.I):
            continue
        dt = parse_date(published)
        out.append({
            'title': title,
            'url': url,
            'image': f'https://i.ytimg.com/vi/{vid}/hqdefault.jpg' if vid else '',
            'source': source,
            'type': 'YOUTUBE',
            'video': True,
            'description': f'{source} video update.',
            'date': format_date(dt) or published[:10],
            'platform': 'youtube',
            'youtube_id': vid,
            'published_at': dt.isoformat() if dt else published,
        })
    return out


def walk_for_tweets(value):
    """Find tweet dictionaries in X's __NEXT_DATA__ regardless of minor schema changes."""
    found = []
    if isinstance(value, dict):
        # Current syndication data normally stores a tweet under content.tweet.
        for key, child in value.items():
            if key == 'tweet' and isinstance(child, dict) and child.get('id_str') and child.get('text'):
                found.append(child)
            found.extend(walk_for_tweets(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(walk_for_tweets(child))
    return found


def tweet_media(tweet):
    media = tweet.get('mediaDetails') or []
    if isinstance(media, list):
        for item in media:
            if not isinstance(item, dict):
                continue
            for key in ('media_url_https', 'display_url', 'url'):
                if item.get(key):
                    return clean(item[key])
            photos = item.get('photos')
            if isinstance(photos, list) and photos:
                if isinstance(photos[0], dict) and photos[0].get('url'):
                    return clean(photos[0]['url'])
    return ''


def parse_x_account(source, handle, keyword_pattern):
    url = f'https://syndication.twitter.com/srv/timeline-profile/screen-name/{handle}'
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        r.raise_for_status()
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text, re.S)
        if not match:
            print('X feed missing __NEXT_DATA__', source)
            return []
        data = json.loads(match.group(1))
    except Exception as e:
        print('X feed failed', source, e)
        return []

    tweets = walk_for_tweets(data.get('props', {}).get('pageProps', {}))
    out = []
    seen = set()
    for tweet in tweets:
        tid = clean(tweet.get('id_str'))
        if not tid or tid in seen:
            continue
        seen.add(tid)
        text = clean(tweet.get('text'))
        if not text or (keyword_pattern and not re.search(keyword_pattern, text, re.I)):
            continue
        dt = parse_date(tweet.get('created_at'))
        image = tweet_media(tweet)
        out.append({
            'title': text,
            'url': f'https://x.com/{handle}/status/{tid}',
            'image': image,
            'source': source,
            'type': 'X',
            'video': False,
            'description': text,
            'date': format_date(dt) or 'Recent',
            'platform': 'x',
            'x_id': tid,
            'published_at': dt.isoformat() if dt else '',
        })
    return out


def load_existing():
    try:
        d = json.loads(OUT.read_text(encoding='utf-8'))
        return d.get('posts', []) if isinstance(d, dict) else []
    except Exception:
        return []


def main():
    posts = []

    # YouTube
    for source, handle, pattern in YOUTUBE_CHANNELS:
        cid = resolve_channel_id(handle)
        if not cid:
            print('No YouTube channel id for', source)
            continue
        feed = f'https://www.youtube.com/feeds/videos.xml?channel_id={cid}'
        posts.extend(parse_atom(source, feed, pattern))

    # X: public account timelines. These are intentionally best-effort; if X
    # blocks the endpoint, the existing feed remains intact rather than blanking.
    for source, handle, pattern in X_ACCOUNTS:
        posts.extend(parse_x_account(source, handle, pattern))

    # Preserve previously collected items so a temporary source failure does
    # not erase the social rail.
    posts.extend(load_existing())

    by = {}
    for p in posts:
        url = clean(p.get('url'))
        title = clean(p.get('title'))
        if not url or not title:
            continue
        # Prefer newly fetched data over an older copy of the same URL.
        if url not in by or p.get('published_at', '') > by[url].get('published_at', ''):
            by[url] = p

    items = list(by.values())

    def key(item):
        dt = parse_date(item.get('published_at'))
        return dt.timestamp() if dt else 0

    items.sort(key=key, reverse=True)
    payload = {
        'updated': datetime.now(timezone.utc).isoformat(),
        'posts': items[:40],
        'profiles': [
            {'name': 'Montana Griz Football on X', 'url': 'https://x.com/MontanaGrizFB'},
            {'name': 'Montana Grizzlies on X', 'url': 'https://x.com/UMGRIZZLIES'},
            {'name': 'Montana Griz Football on Instagram', 'url': 'https://www.instagram.com/montanagrizfootball/'},
            {'name': 'Skyline Sports on X', 'url': 'https://x.com/SkylineSportsMT'},
            {'name': 'Skyline Sports YouTube', 'url': 'https://www.youtube.com/@skylinesports'},
            {'name': 'Big Sky Football on X', 'url': 'https://x.com/BigSkyFB'},
            {'name': 'Big Sky Conference YouTube', 'url': 'https://www.youtube.com/@BigSkyConf'},
        ],
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('Wrote', len(payload['posts']), 'social items')
    print('Fresh X items:', sum(1 for p in payload['posts'] if p.get('platform') == 'x'))
    print('Fresh YouTube items:', sum(1 for p in payload['posts'] if p.get('platform') == 'youtube'))


if __name__ == '__main__':
    main()
