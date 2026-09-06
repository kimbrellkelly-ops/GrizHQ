import json
import re
import html
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs, unquote
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

NEWS_FILE = Path("news.json")
HEADERS = {
    "User-Agent": "GrizHQ-NewsBot/1.0 (+https://grizhq.com)"
}

FEEDS = [
    ("GoGriz", "https://gogriz.com/rss?path=football"),
    ("Google News", "https://news.google.com/rss/search?q=Montana+Grizzlies+football&hl=en-US&gl=US&ceid=US:en"),
]

SKYLINE_URL = "https://skylinesportsmt.com/category/cat-griz-football/"

GRIZ_TERMS = (
    "montana grizzlies", "montana griz", "griz football", "griz", "gillman",
    "bobby kennedy", "keali'i ah yat", "kealii ah yat", "landon ransom-goelz",
    "brooks davis", "washington-grizzly", "washington grizzly", "grizzly stadium"
)
EXCLUDE_TERMS = (
    "montana state", "bobcats", "bobcat", "msu football", "bozeman",
    "cats and griz"  # Avoid generic rivalry stories unless they are clearly Griz-specific.
)

def clean(value):
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()

def parse_date(value):
    value = clean(value)
    if not value:
        return datetime.now(timezone.utc)
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
        except Exception:
            continue
    return datetime.now(timezone.utc)

def is_griz_story(title, description=""):
    text = f"{title} {description}".lower()
    if any(term in text for term in EXCLUDE_TERMS):
        # Let clearly Griz-specific stories through only when they contain a strong Griz term.
        strong = ("montana grizzlies", "montana griz", "griz football", "eli gillman",
                  "bobby kennedy", "keali'i ah yat", "kealii ah yat")
        return any(term in text for term in strong)
    return any(term in text for term in GRIZ_TERMS)

def category(title):
    t = title.lower()
    if any(x in t for x in ("press conference", "post-game", "postgame", "interview", "podcast", "inside the fcs")):
        return "INSIDER"
    if any(x in t for x in ("commit", "commits", "recruit", "recruiting", "offer", "portal", "transfer")):
        return "RECRUITING"
    if any(x in t for x in ("preview", "vs.", "vs ", "against", "look to", "what you should wear", "game day")):
        return "GAME DAY"
    if any(x in t for x in ("recap", "roll past", "outlast", "beats", "beat ", "victory", "wins", "win over")):
        return "GAME STORY"
    if any(x in t for x in ("player of the week", "award", "named", "honor")):
        return "HONOR"
    if any(x in t for x in ("analysis", "numbers", "inside", "breakdown")):
        return "ANALYSIS"
    return "GRIZ NEWS"

def normalize_url(url):
    url = clean(url)
    if not url:
        return ""
    # Google News RSS links can point through news.google.com. Keep them usable.
    return url

def parse_rss(source, url):
    response = requests.get(url, headers=HEADERS, timeout=25)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    items = []
    for item in root.findall(".//item")[:20]:
        title = clean(item.findtext("title"))
        link = clean(item.findtext("link"))
        pub = clean(item.findtext("pubDate"))
        desc = BeautifulSoup(clean(item.findtext("description")), "html.parser").get_text(" ", strip=True)
        if not title or not link or not is_griz_story(title, desc):
            continue

        # Google News titles commonly end in " - Publisher".
        publisher = source
        if source == "Google News" and " - " in title:
            title, publisher = title.rsplit(" - ", 1)

        dt = parse_date(pub)
        items.append({
            "title": clean(title),
            "url": normalize_url(link),
            "date": dt.strftime("%b. %-d, %Y"),
            "published_at": dt.isoformat(),
            "description": clean(desc)[:220],
            "source": publisher,
            "badge": category(title),
            "short": category(title)[:4].upper(),
        })
    return items

def parse_skyline():
    response = requests.get(SKYLINE_URL, headers=HEADERS, timeout=25)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    items = []
    seen = set()

    for a in soup.select("a[href]"):
        title = clean(a.get_text(" ", strip=True))
        href = urljoin(SKYLINE_URL, a.get("href", ""))
        if not title or len(title) < 12 or href in seen:
            continue
        if "skylinesportsmt.com" not in urlparse(href).netloc:
            continue
        if "/category/" in href or "/page/" in href or "/author/" in href:
            continue
        if not is_griz_story(title):
            continue

        # Find a nearby date in the link's parent/container.
        container = a.find_parent(["article", "div", "li"])
        context = clean(container.get_text(" ", strip=True)) if container else ""
        date_match = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+2026", context)
        dt = parse_date(date_match.group(0)) if date_match else datetime.now(timezone.utc)

        items.append({
            "title": title,
            "url": href,
            "date": dt.strftime("%b. %-d, %Y"),
            "published_at": dt.isoformat(),
            "description": context[:220] if context else "Skyline Sports coverage of Montana Grizzlies football.",
            "source": "Skyline Sports",
            "badge": category(title),
            "short": category(title)[:4].upper(),
        })
        seen.add(href)
        if len(items) >= 12:
            break

    return items

def load_existing():
    if not NEWS_FILE.exists():
        return []
    try:
        data = json.loads(NEWS_FILE.read_text(encoding="utf-8"))
        return data.get("stories", []) if isinstance(data, dict) else []
    except Exception as exc:
        print("Could not read existing news.json:", exc)
        return []

def dedupe_and_sort(stories):
    by_key = {}
    for story in stories:
        title = clean(story.get("title"))
        url = normalize_url(story.get("url"))
        if not title or not url:
            continue
        key = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
        # Prefer a real URL as the identity, otherwise use title.
        identity = url if url else key
        current = by_key.get(identity)
        if current is None or parse_date(story.get("published_at") or story.get("date")) > parse_date(current.get("published_at") or current.get("date")):
            story["title"] = title
            story["url"] = url
            story["description"] = clean(story.get("description"))[:220]
            story["badge"] = story.get("badge") or category(title)
            story["short"] = story.get("short") or story["badge"][:4].upper()
            by_key[identity] = story

    result = list(by_key.values())
    result.sort(key=lambda s: parse_date(s.get("published_at") or s.get("date")), reverse=True)
    return result[:24]

def main():
    existing = load_existing()
    fetched = []

    for source, url in FEEDS:
        try:
            items = parse_rss(source, url)
            print(f"{source}: {len(items)} Griz stories")
            fetched.extend(items)
        except Exception as exc:
            print(f"{source} feed failed: {exc}")

    try:
        skyline = parse_skyline()
        print(f"Skyline Sports: {len(skyline)} Griz stories")
        fetched.extend(skyline)
    except Exception as exc:
        print(f"Skyline scrape failed: {exc}")

    merged = dedupe_and_sort(fetched + existing)

    # Safety: never replace a healthy existing feed with an empty/broken result.
    if not merged:
        print("No stories collected; leaving news.json unchanged.")
        return

    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": "Automated Griz HQ news hub",
        "stories": merged,
    }

    NEWS_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(merged)} stories to news.json.")

if __name__ == "__main__":
    main()
