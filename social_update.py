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
    'User-Agent': 'Mozilla/5.0 (compatible; GrizHQ-SocialBot/3.0; +https://grizhq.com)',
    'Accept-Language': 'en-US,en;q=0.9',
}
MAX_ITEMS = 40
MAX_AGE_DAYS = 7
REQUEST_TIMEOUT = 25

# These are intentionally stable public pages. We do NOT use X syndication,
# Nitter, TwStalker, or YouTube Atom feeds because those endpoints have proven
# unreliable in GitHub Actions.
X_MIRRORS = [
    ('Montana Griz Football on X', 'MontanaGrizFB', 'https://www.24vids.com/channel/montanagrizfb'),
    ('Montana Grizzlies on X', 'UMGRIZZLIES', 'https://www.24vids.com/channel/umgrizzlies'),
    ('Big Sky Football on X', 'BigSkyFB', 'https://www.24vids.com/channel/bigskyfb'),
]

SKYLINE_VIDEO_PAGE = 'https://skylinesportsmt.com/skyline-sports-youtube/'
SKYLINE_WP_API = 'https://skylinesportsmt.com/wp-json/wp/v2/pages?slug=skyline-sports-youtube&per_page=5'

VIDEO_RE = re.compile(r'(?:youtube(?:-nocookie)?\.com/(?:embed/|watch\?v=|shorts/)|youtu\.be/|i\.ytimg\.com/vi/)([A-Za-z0-9_-]{11})', re.I)
DATE_RE = re.compile(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:,\s*\d{4})?\b', re.I)
REL_RE = re.compile(r'\b(\d+)\s*(second|minute|min|hour|hr|day|week)s?\s+ago\b', re.I)


def clean(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def parse_dt(value):
    if not value:
        return None
    text = clean(value)
    now = datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(text.replace('Z', '+00:00')).astimezone(timezone.utc)
    except Exception:
        pass
    m = REL_RE.search(text)
    if m:
        n = int(m.group(1)); unit = m.group(2).lower()
        units = {
            'second': timedelta(seconds=n), 'minute': timedelta(minutes=n), 'min': timedelta(minutes=n),
            'hour': timedelta(hours=n), 'hr': timedelta(hours=n), 'day': timedelta(days=n),
            'week': timedelta(weeks=n),
        }
        return now - units[unit]
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
    return dt.strftime('%b. %-d, %Y') if dt else ''


def request(url):
    r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r


def dedupe(posts):
    by = {}
    for p in posts:
        url = clean(p.get('url'))
        title = clean(p.get('title'))
        if url and title:
            by[url] = p
    return list(by.values())


def make_social_post(title, url, handle, dt, image=''):
    return {
        'title': title,
        'url': url,
        'image': image,
        'source': f'@{handle} on X',
        'type': 'SOCIAL',
        'video': False,
        'description': f'Public social post from @{handle}.',
        'date': fmt_date(dt),
        'platform': 'x',
        'published_at': dt.isoformat() if dt else '',
    }


def x_from_24vids(label, handle, page_url):
    """Parse the public 24vids mirror of an X profile.

    24vids is used only as a public mirror. If it is unavailable or stale,
    the source is skipped; it can never make the workflow fail by itself.
    """
    out = []
    try:
        r = request(page_url)
        soup = BeautifulSoup(r.text, 'html.parser')
        # 24vids profile pages expose individual post links. Walk each link's
        # nearest useful container and look for relative dates such as '7 hours ago'.
        for a in soup.find_all('a', href=True):
            href = urljoin(r.url, a.get('href', ''))
            if '24vids.com' not in href or href.rstrip('/') == page_url.rstrip('/'):
                continue
            text = clean(a.get_text(' ', strip=True))
            if len(text) < 8:
                continue
            container = a
            for _ in range(5):
                if container.parent:
                    container = container.parent
            block = clean(container.get_text(' ', strip=True))
            if handle.lower() not in block.lower() and 'goGriz' not in block and '#GoGriz' not in block:
                # Still accept a profile page's own post links when the title is useful.
                if not any(k in text.lower() for k in ('griz', 'montana', 'gogriz')):
                    continue
            dt = parse_dt(block) or parse_dt(a.get('title')) or parse_dt(a.get('datetime'))
            if not dt:
                continue
            # Avoid profile/category/navigation links.
            if len(text) > 400:
                text = text[:397] + '...'
            img = container.find('img')
            image = clean((img.get('src') or img.get('data-src')) if img else '')
            out.append(make_social_post(text, href, handle, dt, image))
    except Exception as exc:
        print(f'{label}: 24vids unavailable: {exc}')
    return dedupe(out)


def parse_skyline_html(html, base_url):
    """Parse Skyline's video cards directly from thumbnail URLs.

    Skyline's public page exposes the YouTube thumbnail as the clickable link
    and renders the title/date as neighboring text rather than putting the
    YouTube URL in the anchor. Parse the card around each i.ytimg thumbnail so
    the updater is independent of that presentation detail.
    """
    soup = BeautifulSoup(html, 'html.parser')
    out = []

    def duration_remainder(text):
        return re.sub(r'\b\d{1,2}:\d{2}(?::\d{2})?\b', ' ', text)

    def extract_title(container, block):
        # First try visible text nodes immediately associated with the card.
        candidates = []
        for node in container.find_all(string=True):
            t = clean(node)
            if not t or re.fullmatch(r'\d{1,2}:\d{2}(?::\d{2})?', t):
                continue
            if DATE_RE.fullmatch(t) or re.fullmatch(r'\d{1,2}\s*(?:seconds?|minutes?|hours?|days?)\s+ago', t, re.I):
                continue
            candidates.append(t)
        # Prefer a substantial title-like node containing Griz/Montana/Big Sky.
        for t in candidates:
            if len(t) >= 12 and re.search(r'\b(Montana|Griz|Grizzlies|Big Sky|FCS|Utah Tech|Drake|Southern Utah)\b', t, re.I):
                return t[:500]
        for t in candidates:
            if len(t) >= 12:
                return t[:500]
        # Last resort: clean the combined card text.
        cleaned = duration_remainder(block)
        cleaned = DATE_RE.sub(' ', cleaned)
        cleaned = REL_RE.sub(' ', cleaned)
        return clean(cleaned)[:500]

    # Directly inspect every Skyline YouTube thumbnail. This is the reliable
    # identifier exposed by the current page (e.g. i.ytimg.com/vi/<id>/...).
    for img in soup.find_all('img'):
        src = clean(img.get('src') or img.get('data-src') or img.get('data-lazy-src'))
        m = VIDEO_RE.search(src)
        if not m:
            continue
        video_id = m.group(1)
        container = img
        best = None
        for _ in range(8):
            if not container.parent:
                break
            container = container.parent
            block = clean(container.get_text(' ', strip=True))
            dt = parse_dt(block)
            if dt and 20 <= len(block) <= 1500:
                best = (container, block, dt)
                # Stop once the container looks like a single video card.
                if re.search(r'\b\d{1,2}:\d{2}(?::\d{2})?\b', block) and len(block) <= 700:
                    break
        if not best:
            continue
        container, block, dt = best
        title = extract_title(container, block)
        if not title:
            continue
        if not re.search(r'\b(Montana|Griz|Grizzlies|Big Sky|FCS|Utah Tech|Drake|Southern Utah)\b', title, re.I):
            continue
        out.append({
            'title': title,
            'url': f'https://www.youtube.com/watch?v={video_id}',
            'image': src,
            'source': 'Skyline Sports YouTube',
            'type': 'YOUTUBE',
            'video': True,
            'description': 'Verified Montana/Big Sky video from Skyline Sports.',
            'date': fmt_date(dt),
            'platform': 'youtube',
            'youtube_id': video_id,
            'published_at': dt.isoformat(),
        })
    return dedupe(out)


def skyline_videos():
    # Direct public page first.
    try:
        r = request(SKYLINE_VIDEO_PAGE)
        out = parse_skyline_html(r.text, r.url)
        if out:
            return out
        print('Skyline video page returned no parsable videos; trying WordPress API.')
    except Exception as exc:
        print('Skyline video page failed:', exc)
    # WordPress API fallback. The page content is public and generally more stable
    # for automated retrieval than the rendered page.
    try:
        r = request(SKYLINE_WP_API)
        data = r.json()
        if isinstance(data, list):
            for page in data:
                content = ((page.get('content') or {}).get('rendered') or '')
                out = parse_skyline_html(content, 'https://skylinesportsmt.com/')
                if out:
                    return out
    except Exception as exc:
        print('Skyline WordPress API failed:', exc)
    return []


def load_existing():
    try:
        data = json.loads(OUT.read_text(encoding='utf-8'))
        return data.get('posts', []) if isinstance(data, dict) else []
    except Exception:
        return []


def post_dt(post):
    return parse_dt(post.get('published_at'))


def main():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=MAX_AGE_DAYS)
    posts = []
    fresh_sources = []

    # Public X mirrors: never let a blocked mirror abort the entire updater.
    for label, handle, page in X_MIRRORS:
        found = [p for p in x_from_24vids(label, handle, page) if post_dt(p) and post_dt(p) >= cutoff]
        if found:
            fresh_sources.append(label)
            posts.extend(found)
            print(f'{label}: {len(found)} fresh posts via 24vids')
        else:
            print(f'{label}: no fresh posts via 24vids')

    # Skyline is our dependable video source and is independent of X/YouTube APIs.
    skyline = [p for p in skyline_videos() if post_dt(p) and post_dt(p) >= cutoff]
    if skyline:
        fresh_sources.append('Skyline Sports video index')
        posts.extend(skyline)
        print(f'Skyline Sports video index: {len(skyline)} fresh videos')
    else:
        print('Skyline Sports video index: no fresh videos found')

    # Keep only recent cached items. Nothing older than seven days can survive.
    existing = [p for p in load_existing() if post_dt(p) and post_dt(p) >= cutoff]
    posts.extend(existing)
    posts = dedupe(posts)
    posts.sort(key=lambda p: post_dt(p) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    # The workflow should fail only when we truly have no usable fresh source.
    # Cached recent posts alone are not considered a successful refresh.
    if not fresh_sources:
        print('ERROR: No fresh social source was retrieved. Refusing to publish a stale feed.')
        sys.exit(1)

    if not posts or not post_dt(posts[0]) or post_dt(posts[0]) < cutoff:
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
    print(f'Wrote {len(payload["posts"])} social items from {len(fresh_sources)} fresh sources: {", ".join(fresh_sources)}')


if __name__ == '__main__':
    main()
