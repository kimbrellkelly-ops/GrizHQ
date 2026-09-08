import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

OUT = Path('social.json')
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; GrizHQ-SocialBot/2.0; +https://grizhq.com)'
}
MAX_ITEMS = 40
MAX_AGE_DAYS = 7
REQUEST_TIMEOUT = 20

X_ACCOUNTS = [
    ('Montana Griz Football on X', 'MontanaGrizFB'),
    ('Montana Grizzlies on X', 'UMGRIZZLIES'),
    ('Big Sky Football on X', 'BigSkyFB'),
]

YOUTUBE_CHANNELS = [
    ('Skyline Sports YouTube', 'https://www.youtube.com/@skylinesports'),
    ('Montana Griz Football YouTube', 'https://www.youtube.com/@MontanaGrizFB'),
    ('Big Sky Conference YouTube', 'https://www.youtube.com/@BigSkyConf'),
]

VIDEO_RE = re.compile(r'(?:youtube(?:-nocookie)?\.com/(?:embed/|watch\?v=|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})', re.I)
STATUS_RE = re.compile(r'https?://(?:x\.com|twitter\.com)/([A-Za-z0-9_]+)/status/(\d+)', re.I)
DATE_RE = re.compile(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:,\s*\d{4})?\b', re.I)


def clean(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def parse_dt(value):
    if not value:
        return None
    text = clean(value)
    now = datetime.now(timezone.utc)
    # ISO / RFC-ish values
    try:
        return datetime.fromisoformat(text.replace('Z', '+00:00')).astimezone(timezone.utc)
    except Exception:
        pass
    # Relative labels used by public profile mirrors
    m = re.search(r'(\d+)\s*(minute|min|hour|hr|day|week)s?\s+ago', text, re.I)
    if m:
        n = int(m.group(1)); unit = m.group(2).lower()
        delta = {'minute': timedelta(minutes=n), 'min': timedelta(minutes=n),
                 'hour': timedelta(hours=n), 'hr': timedelta(hours=n),
                 'day': timedelta(days=n), 'week': timedelta(weeks=n)}[unit]
        return now - delta
    if re.search(r'\byesterday\b', text, re.I):
        return now - timedelta(days=1)
    m = DATE_RE.search(text)
    if m:
        raw = m.group(0).replace('.', '')
        for fmt in ('%b %d, %Y', '%B %d, %Y', '%b %d', '%B %d'):
            try:
                dt = datetime.strptime(raw, fmt)
                if '%Y' not in fmt:
                    dt = dt.replace(year=now.year)
                    if dt > now.replace(tzinfo=None):
                        dt = dt.replace(year=dt.year - 1)
                return dt.replace(tzinfo=timezone.utc)
            except Exception:
                continue
    return None


def fmt_date(dt):
    if not dt:
        return ''
    return dt.strftime('%b. %-d, %Y')


def request(url):
    r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r


def x_from_syndication(handle):
    urls = [
        f'https://syndication.twitter.com/srv/timeline-profile/screen-name/{handle}?lang=en',
        f'https://syndication.twitter.com/widgets/timelines/profile?screen_name={handle}&lang=en',
    ]
    posts = []
    for url in urls:
        try:
            r = request(url)
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=STATUS_RE):
                href = a.get('href', '')
                m = STATUS_RE.search(href)
                if not m:
                    continue
                container = a
                for _ in range(5):
                    if container.parent:
                        container = container.parent
                text = clean(container.get_text(' ', strip=True))
                title = clean(a.get_text(' ', strip=True)) or text
                dt = parse_dt(container.get_text(' ', strip=True))
                if not dt:
                    dt = parse_dt(a.get('title')) or parse_dt(a.get('datetime'))
                posts.append(make_x_post(title, href, handle, dt, container))
            if posts:
                return dedupe(posts)
        except Exception as exc:
            print(f'X syndication failed for @{handle}: {exc}')
    return []


def x_from_public_mirror(handle):
    # TwStalker currently exposes public timelines without an API key.
    urls = [f'https://twstalker.com/{handle}', f'https://source.twstalker.com/{handle}']
    posts = []
    for url in urls:
        try:
            r = request(url)
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = urljoin(r.url, a['href'])
                m = STATUS_RE.search(href)
                if not m or m.group(1).lower() != handle.lower():
                    continue
                container = a
                for _ in range(8):
                    if container.parent:
                        container = container.parent
                text = clean(container.get_text(' ', strip=True))
                # Avoid navigation/profile links that happen to contain a status URL.
                if len(text) < 8:
                    continue
                dt = parse_dt(text) or parse_dt(a.get('title')) or parse_dt(a.get('datetime'))
                title = clean(text)
                if len(title) > 300:
                    title = title[:297] + '...'
                posts.append(make_x_post(title, href, handle, dt, container))
            if posts:
                return dedupe(posts)
        except Exception as exc:
            print(f'X public mirror failed for @{handle}: {exc}')
    return []


def make_x_post(title, url, handle, dt, container=None):
    image = ''
    if container:
        img = container.find('img')
        if img:
            image = clean(img.get('src') or img.get('data-src'))
    return {
        'title': title or f'@{handle} post',
        'url': url,
        'image': image,
        'source': f'@{handle} on X',
        'type': 'SOCIAL',
        'video': False,
        'description': f'Public post from @{handle}.',
        'date': fmt_date(dt),
        'platform': 'x',
        'published_at': dt.isoformat() if dt else '',
    }


def resolve_channel_id(handle_url):
    try:
        r = request(handle_url)
        text = r.text
        patterns = [
            r'"channelId":"(UC[A-Za-z0-9_-]+)"',
            r'"externalId":"(UC[A-Za-z0-9_-]+)"',
            r'/channel/(UC[A-Za-z0-9_-]+)',
        ]
        for pattern in patterns:
            m = re.search(pattern, text)
            if m:
                return m.group(1)
    except Exception as exc:
        print('YouTube channel resolve failed', handle_url, exc)
    return ''


def parse_atom(source, feed_url, keyword_pattern=''):
    try:
        r = request(feed_url)
        root = ET.fromstring(r.content)
    except Exception as exc:
        print('YouTube feed failed', source, exc)
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
            m = VIDEO_RE.search(url); vid = m.group(1) if m else ''
        if not title or not url:
            continue
        if keyword_pattern and not re.search(keyword_pattern, title, re.I):
            continue
        dt = parse_dt(published)
        out.append({
            'title': title, 'url': url,
            'image': f'https://i.ytimg.com/vi/{vid}/hqdefault.jpg' if vid else '',
            'source': source, 'type': 'YOUTUBE', 'video': True,
            'description': f'{source} video update.', 'date': fmt_date(dt),
            'platform': 'youtube', 'youtube_id': vid,
            'published_at': dt.isoformat() if dt else published,
        })
    return out


def skyline_page_videos():
    url = 'https://skylinesportsmt.com/skyline-sports-youtube/'
    out = []
    try:
        r = request(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = urljoin(r.url, a['href'])
            m = VIDEO_RE.search(href)
            if not m:
                continue
            title = clean(a.get_text(' ', strip=True))
            if not title or len(title) < 5:
                continue
            container = a
            for _ in range(5):
                if container.parent:
                    container = container.parent
            text = clean(container.get_text(' ', strip=True))
            dt = parse_dt(text)
            if not dt:
                # Search nearby page text for an explicit date.
                dt = parse_dt(DATE_RE.search(text).group(0)) if DATE_RE.search(text) else None
            img = container.find('img')
            image = clean((img.get('src') or img.get('data-src')) if img else '')
            out.append({
                'title': title, 'url': href, 'image': image or f'https://i.ytimg.com/vi/{m.group(1)}/hqdefault.jpg',
                'source': 'Skyline Sports YouTube', 'type': 'YOUTUBE', 'video': True,
                'description': 'Verified Montana Griz video from Skyline Sports.',
                'date': fmt_date(dt), 'platform': 'youtube', 'youtube_id': m.group(1),
                'published_at': dt.isoformat() if dt else '',
            })
    except Exception as exc:
        print('Skyline video page failed:', exc)
    return dedupe(out)


def load_existing():
    try:
        data = json.loads(OUT.read_text(encoding='utf-8'))
        return data.get('posts', []) if isinstance(data, dict) else []
    except Exception:
        return []


def post_dt(post):
    return parse_dt(post.get('published_at'))


def dedupe(posts):
    by = {}
    for p in posts:
        url = clean(p.get('url'))
        title = clean(p.get('title'))
        if not url or not title:
            continue
        by[url] = p
    return list(by.values())


def main():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=MAX_AGE_DAYS)
    fresh_sources = []
    posts = []

    # X: try official syndication first, then a public timeline mirror.
    for source, handle in X_ACCOUNTS:
        found = x_from_syndication(handle)
        if not found:
            found = x_from_public_mirror(handle)
        fresh = [p for p in found if post_dt(p) and post_dt(p) >= cutoff]
        if fresh:
            fresh_sources.append(source)
            posts.extend(fresh)
            print(f'{source}: {len(fresh)} fresh posts')
        else:
            print(f'{source}: no fresh posts found')

    # YouTube Atom feeds plus Skyline's public video index as a direct fallback.
    for source, handle_url in YOUTUBE_CHANNELS:
        cid = resolve_channel_id(handle_url)
        found = []
        if cid:
            pattern = 'MONTANA|GRIZ|BIG SKY|FCS|SOUTHERN UTAH|DRAKE|UTAH TECH|IDAHO|FOOTBALL'
            found = parse_atom(source, f'https://www.youtube.com/feeds/videos.xml?channel_id={cid}', pattern)
        fresh = [p for p in found if post_dt(p) and post_dt(p) >= cutoff]
        if fresh:
            fresh_sources.append(source)
            posts.extend(fresh)
            print(f'{source}: {len(fresh)} fresh videos')
        else:
            print(f'{source}: no fresh videos from Atom')

    skyline = [p for p in skyline_page_videos() if post_dt(p) and post_dt(p) >= cutoff]
    if skyline:
        fresh_sources.append('Skyline Sports video index')
        posts.extend(skyline)
        print(f'Skyline Sports video index: {len(skyline)} fresh videos')

    # Preserve recent existing items only. Never let stale content survive forever.
    existing = [p for p in load_existing() if post_dt(p) and post_dt(p) >= cutoff]
    posts.extend(existing)

    posts = dedupe(posts)
    posts.sort(key=lambda p: post_dt(p) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    # A successful run must have a fresh source. If everything failed, fail loudly
    # instead of publishing a two-week-old feed and pretending the refresh worked.
    if not fresh_sources:
        print('ERROR: No fresh social source was retrieved. Refusing to publish a stale feed.')
        sys.exit(1)

    # Require at least one genuinely current item, not just a recent cached item.
    newest = post_dt(posts[0]) if posts else None
    if not newest or newest < cutoff:
        print('ERROR: No social item is within the freshness window.')
        sys.exit(1)

    payload = {
        'updated': now.isoformat(),
        'posts': posts[:MAX_ITEMS],
        'profiles': [
            {'name': 'Montana Griz Football on X', 'url': 'https://x.com/MontanaGrizFB'},
            {'name': 'Montana Grizzlies on X', 'url': 'https://x.com/UMGRIZZLIES'},
            {'name': 'Montana Griz Football on Instagram', 'url': 'https://www.instagram.com/montanagrizfootball/'},
            {'name': 'Skyline Sports YouTube', 'url': 'https://www.youtube.com/@skylinesports'},
            {'name': 'Big Sky Football on X', 'url': 'https://x.com/BigSkyFB'},
            {'name': 'Big Sky Conference YouTube', 'url': 'https://www.youtube.com/@BigSkyConf'},
        ],
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {len(payload["posts"])} social items from {len(fresh_sources)} fresh sources.')


if __name__ == '__main__':
    main()
