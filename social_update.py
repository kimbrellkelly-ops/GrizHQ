import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

OUT = Path('social.json')
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; GrizHQ-SocialBot/2.0; +https://grizhq.com)',
    'Accept-Language': 'en-US,en;q=0.9',
}

# X has repeatedly changed/blocked public access methods.  Try several public
# RSS/mirror endpoints, but never make one third-party mirror a hard dependency.
X_ACCOUNTS = [
    ('Montana Griz Football on X', 'MontanaGrizFB'),
    ('Montana Grizzlies on X', 'UMGRIZZLIES'),
    ('Big Sky Football on X', 'BigSkyFB'),
]
X_RSS_ENDPOINTS = [
    'https://xcancel.com/{user}/rss',
    'https://nitter.poast.org/{user}/rss',
    'https://nitter.privacyredirect.com/{user}/rss',
    'https://nitter.tiekoetter.com/{user}/rss',
]
X_HTML_ENDPOINTS = [
    'https://twitterviewer.io/profile/{user}',
]

SKYLINE_VIDEO_PAGE = 'https://skylinesportsmt.com/skyline-sports-youtube/'

FRESH_DAYS = 7
MAX_ITEMS = 40


def clean(v):
    return re.sub(r'\s+', ' ', str(v or '')).strip()


def parse_dt(value):
    value = clean(value)
    if not value:
        return None
    candidates = [value, value.replace('Z', '+00:00')]
    for candidate in candidates:
        try:
            dt = datetime.fromisoformat(candidate)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass
    for fmt in (
        '%a, %d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y %H:%M:%S GMT',
        '%Y-%m-%d',
        '%B %d, %Y',
        '%b %d, %Y',
    ):
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass
    return None


def fmt_date(dt):
    if not dt:
        return 'Recent'
    return dt.strftime('%b. %-d, %Y')


def request(url, timeout=20):
    return requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)


def parse_feed(source, content):
    """Parse RSS/Atom XML from an X mirror into our common social format."""
    try:
        root = ET.fromstring(content)
    except Exception:
        return []

    out = []
    # RSS 2.0
    for item in root.findall('.//item'):
        title = clean(item.findtext('title'))
        url = clean(item.findtext('link'))
        pub = clean(item.findtext('pubDate') or item.findtext('published') or item.findtext('updated'))
        desc = clean(item.findtext('description'))
        dt = parse_dt(pub)
        if title and url:
            out.append({
                'title': title,
                'url': url,
                'image': '',
                'source': source,
                'type': 'X',
                'video': False,
                'description': desc or f'{source} social post.',
                'date': fmt_date(dt),
                'platform': 'x',
                'published_at': dt.isoformat() if dt else pub,
            })

    # Atom / Nitter-style feeds
    ns = '{http://www.w3.org/2005/Atom}'
    for entry in root.findall(f'.//{ns}entry'):
        title = clean(entry.findtext(f'{ns}title'))
        link_node = entry.find(f'{ns}link')
        url = clean(link_node.attrib.get('href', '') if link_node is not None else '')
        pub = clean(entry.findtext(f'{ns}published') or entry.findtext(f'{ns}updated'))
        summary = clean(entry.findtext(f'{ns}summary'))
        dt = parse_dt(pub)
        if title and url:
            out.append({
                'title': title,
                'url': url,
                'image': '',
                'source': source,
                'type': 'X',
                'video': False,
                'description': summary or f'{source} social post.',
                'date': fmt_date(dt),
                'platform': 'x',
                'published_at': dt.isoformat() if dt else pub,
            })
    return out


def fetch_x_rss(display_name, user):
    for template in X_RSS_ENDPOINTS:
        url = template.format(user=user)
        try:
            r = request(url)
            if r.status_code != 200:
                print(f'X RSS {display_name}: {r.status_code} {url}')
                continue
            posts = parse_feed(display_name, r.content)
            if posts:
                print(f'X RSS {display_name}: {len(posts)} posts from {url}')
                return posts
            print(f'X RSS {display_name}: empty feed from {url}')
        except Exception as e:
            print(f'X RSS {display_name}: failed {url}: {e}')
    return []


def fetch_x_html(display_name, user):
    """Best-effort fallback for public mirror pages that expose post text/links."""
    for template in X_HTML_ENDPOINTS:
        url = template.format(user=user)
        try:
            r = request(url)
            if r.status_code != 200:
                print(f'X HTML {display_name}: {r.status_code} {url}')
                continue
            soup = BeautifulSoup(r.text, 'html.parser')
            found = []
            for a in soup.find_all('a', href=True):
                href = a.get('href', '')
                if '/status/' not in href:
                    continue
                title = clean(a.get_text(' ', strip=True))
                if not title or title.startswith('@'):
                    continue
                full = urljoin(r.url, href)
                # Try to find a nearby timestamp.
                parent = a.parent
                raw = clean(parent.get_text(' ', strip=True) if parent else '')
                dt = parse_dt(raw)
                found.append({
                    'title': title,
                    'url': full,
                    'image': '',
                    'source': display_name,
                    'type': 'X',
                    'video': False,
                    'description': f'{display_name} social post.',
                    'date': fmt_date(dt),
                    'platform': 'x',
                    'published_at': dt.isoformat() if dt else '',
                })
            if found:
                print(f'X HTML {display_name}: {len(found)} posts from {url}')
                return found
        except Exception as e:
            print(f'X HTML {display_name}: failed {url}: {e}')
    return []


def fetch_skyline_videos():
    """Skyline maintains a current public video index that is more reliable than its YouTube Atom feed."""
    try:
        r = request(SKYLINE_VIDEO_PAGE)
        r.raise_for_status()
    except Exception as e:
        print('Skyline video page failed:', e)
        return []

    soup = BeautifulSoup(r.text, 'html.parser')
    out = []
    seen = set()
    for a in soup.find_all('a', href=True):
        href = a.get('href', '')
        m = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})', href)
        if not m:
            continue
        vid = m.group(1)
        if vid in seen:
            continue
        seen.add(vid)
        title = clean(a.get_text(' ', strip=True))
        if not title:
            # Some WordPress video cards keep the title in an adjacent heading.
            parent = a.parent
            title = clean(parent.get_text(' ', strip=True) if parent else '')
        if not title:
            continue
        # Keep the feed Griz-focused. Skyline's page includes MSU content too.
        hay = title.lower()
        if not re.search(r'\bgriz\b|montana|big sky', hay, re.I):
            continue
        container_text = clean(a.parent.parent.get_text(' ', strip=True) if a.parent and a.parent.parent else '')
        dt = None
        # Search for a visible month/day/year date near the video card.
        md = re.search(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b', container_text)
        if md:
            dt = parse_dt(md.group(0))
        out.append({
            'title': title,
            'url': f'https://www.youtube.com/watch?v={vid}',
            'image': f'https://i.ytimg.com/vi/{vid}/hqdefault.jpg',
            'source': 'Skyline Sports YouTube',
            'type': 'YOUTUBE',
            'video': True,
            'description': 'Verified Montana Griz video from Skyline Sports.',
            'date': fmt_date(dt),
            'platform': 'youtube',
            'youtube_id': vid,
            'published_at': dt.isoformat() if dt else '',
        })
    print(f'Skyline video index: {len(out)} Griz videos found')
    return out


def load_existing():
    try:
        d = json.loads(OUT.read_text(encoding='utf-8'))
        return d.get('posts', []) if isinstance(d, dict) else []
    except Exception:
        return []


def normalize_existing(items):
    cutoff = datetime.now(timezone.utc) - timedelta(days=FRESH_DAYS)
    out = []
    for p in items:
        dt = parse_dt(p.get('published_at'))
        if dt is None:
            # Old records with only a display date are retained only if the date parses.
            dt = parse_dt(p.get('date'))
        if dt is None or dt < cutoff:
            continue
        q = dict(p)
        q['published_at'] = dt.isoformat()
        out.append(q)
    return out


def main():
    fresh = []

    # X: best-effort; failures are logged but do not block Skyline from updating.
    for display_name, user in X_ACCOUNTS:
        posts = fetch_x_rss(display_name, user)
        if not posts:
            posts = fetch_x_html(display_name, user)
        fresh.extend(posts)
        if posts:
            print(f'{display_name}: {len(posts)} fresh candidates')
        else:
            print(f'{display_name}: no fresh posts found')

    # Skyline: independent of YouTube's deprecated/blocked Atom endpoints.
    fresh.extend(fetch_skyline_videos())

    # Only keep recent previous items as a short-term outage buffer.
    existing = normalize_existing(load_existing())

    by_url = {}
    for p in existing + fresh:
        url = clean(p.get('url'))
        title = clean(p.get('title'))
        if not url or not title:
            continue
        by_url[url] = p

    items = list(by_url.values())
    cutoff = datetime.now(timezone.utc) - timedelta(days=FRESH_DAYS)
    recent = []
    for p in items:
        dt = parse_dt(p.get('published_at'))
        if dt is None or dt < cutoff:
            continue
        recent.append(p)

    def key(x):
        dt = parse_dt(x.get('published_at'))
        return dt.timestamp() if dt else 0

    recent.sort(key=key, reverse=True)

    # Do not silently publish an ancient/stale feed. At least one current source
    # must have produced something or a recent existing item must still be present.
    fresh_now = [p for p in fresh if (parse_dt(p.get('published_at')) or datetime.min.replace(tzinfo=timezone.utc)) >= cutoff]
    if not fresh_now and not recent:
        raise RuntimeError('No fresh social source was retrieved. Refusing to publish a stale feed.')

    payload = {
        'updated': datetime.now(timezone.utc).isoformat(),
        'posts': recent[:MAX_ITEMS],
        'profiles': [
            {'name': 'Montana Griz Football on X', 'url': 'https://x.com/MontanaGrizFB'},
            {'name': 'Montana Grizzlies on X', 'url': 'https://x.com/UMGRIZZLIES'},
            {'name': 'Montana Griz Football on Instagram', 'url': 'https://www.instagram.com/montanagrizfootball/'},
            {'name': 'Skyline Sports YouTube', 'url': 'https://www.youtube.com/@skylinesports'},
            {'name': 'Big Sky Conference', 'url': 'https://x.com/BigSkyConf'},
        ],
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {len(payload["posts"])} social items; {len(fresh_now)} fresh items retrieved this run.')


if __name__ == '__main__':
    main()
