import json
import re
import html
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

NEWS_FILE = Path("news.json")
HEADERS = {
    "User-Agent": "GrizHQ-NewsBot/1.1 (+https://grizhq.com)"
}

FEEDS = [
    ("GoGriz", "https://gogriz.com/rss?path=football"),
    ("Google News", "https://news.google.com/rss/search?q=Montana+Grizzlies+football&hl=en-US&gl=US&ceid=US:en"),
]

SKYLINE_URL = "https://skylinesportsmt.com/category/cat-griz-football/"
FALLBACK_IMAGE = "hero.jpg"

GRIZ_TERMS = (
    "montana grizzlies", "montana griz", "griz football", "griz", "gillman",
    "bobby kennedy", "keali'i ah yat", "kealii ah yat", "landon ransom-goelz",
    "brooks davis", "washington-grizzly", "washington grizzly", "grizzly stadium"
)
EXCLUDE_TERMS = (
    "montana state", "bobcats", "bobcat", "msu football", "bozeman",
    "cats and griz"
)

IMAGE_CACHE = {}

VIDEO_RE = re.compile(r"(?:youtube(?:-nocookie)?\.com/(?:embed/|watch\?v=|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})", re.I)


def extract_youtube_id(text):
    match = VIDEO_RE.search(text or "")
    return match.group(1) if match else ""


def video_thumbnail(video_id):
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" if video_id else ""


def looks_like_video(title, url="", text=""):
    hay = f"{title} {url} {text}".lower()
    return bool(extract_youtube_id(hay) or any(term in hay for term in (
        "watch –", "watch -", "video", "press conference", "interview", "podcast", "postgame", "post-game", "highlights"
    )))


def clean(value):
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def parse_date(value):
    value = clean(value)
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
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
    return datetime.min.replace(tzinfo=timezone.utc)


def is_griz_story(title, description=""):
    text = f"{title} {description}".lower()
    if any(term in text for term in EXCLUDE_TERMS):
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
    if any(x in t for x in ("utah tech", "trailblazers", "opponent", "byu")):
        return "OPPONENT"
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
    return clean(url)


def valid_image(url):
    if not url:
        return ""
    url = clean(url)
    if url.startswith("//"):
        url = "https:" + url
    if not url.lower().startswith(("http://", "https://")):
        return ""
    low = url.lower()
    if any(x in low for x in ("logo", "avatar", "icon", "tracking", "pixel", "griz-hq")):
        return ""
    return url


def image_from_rss_item(item, base_url):
    # Common RSS media/enclosure formats.
    candidates = []
    for tag in (
        "{http://search.yahoo.com/mrss/}content",
        "{http://search.yahoo.com/mrss/}thumbnail",
        "{http://search.yahoo.com/mrss/}group",
        "enclosure",
    ):
        for node in item.findall(f".//{tag}"):
            candidates.append(node.attrib.get("url") or node.attrib.get("href") or "")
    for raw in candidates:
        image = valid_image(urljoin(base_url, raw))
        if image:
            return image
    return ""


def fetch_article_metadata(url):
    """Return featured image and published date from an article page.

    Priority: og:image, twitter:image, schema/image, then first meaningful article image.
    The function is cached for the duration of one updater run.
    """
    url = normalize_url(url)
    if not url:
        return {"image": "", "published_at": ""}
    if url in IMAGE_CACHE:
        return IMAGE_CACHE[url]

    result = {"image": "", "published_at": "", "youtube_id": "", "video_thumbnail": ""}
    try:
        response = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        result["youtube_id"] = extract_youtube_id(response.text)
        if result["youtube_id"]:
            result["video_thumbnail"] = video_thumbnail(result["youtube_id"])

        for attrs in (
            {"property": "og:image"},
            {"name": "twitter:image"},
            {"itemprop": "image"},
        ):
            node = soup.find("meta", attrs=attrs)
            if node and node.get("content"):
                result["image"] = valid_image(urljoin(response.url, node["content"]))
                if result["image"]:
                    break

        if not result["image"]:
            for node in soup.select("article img, main img"):
                src = node.get("src") or node.get("data-src") or node.get("data-lazy-src")
                image = valid_image(urljoin(response.url, src or ""))
                if image:
                    result["image"] = image
                    break

        date_node = (
            soup.find("meta", attrs={"property": "article:published_time"})
            or soup.find("meta", attrs={"name": "date"})
            or soup.find("meta", attrs={"itemprop": "datePublished"})
        )
        if date_node and date_node.get("content"):
            result["published_at"] = date_node["content"].strip()
        else:
            time_node = soup.find("time", attrs={"datetime": True})
            if time_node:
                result["published_at"] = time_node.get("datetime", "").strip()
    except Exception as exc:
        print(f"Metadata fetch failed for {url}: {exc}")

    IMAGE_CACHE[url] = result
    return result


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

        publisher = source
        if source == "Google News" and " - " in title:
            title, publisher = title.rsplit(" - ", 1)

        dt = parse_date(pub)
        rss_image = image_from_rss_item(item, link)
        meta = fetch_article_metadata(link)
        image = rss_image or meta.get("image", "")
        youtube_id = meta.get("youtube_id", "")
        is_video = looks_like_video(title, link, desc) or bool(youtube_id)

        items.append({
            "title": clean(title),
            "url": normalize_url(link),
            "date": dt.strftime("%b. %-d, %Y") if dt != datetime.min.replace(tzinfo=timezone.utc) else "",
            "published_at": dt.isoformat() if dt != datetime.min.replace(tzinfo=timezone.utc) else "",
            "description": clean(desc)[:220],
            "source": publisher,
            "badge": category(title),
            "short": category(title)[:4].upper(),
            "image": image,
            "is_video": is_video,
            "youtube_id": youtube_id,
            "video_url": f"https://www.youtube.com/watch?v={youtube_id}" if youtube_id else (link if is_video else ""),
            "video_thumbnail": meta.get("video_thumbnail", "") or image,
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

        container = a.find_parent(["article", "div", "li"])
        context = clean(container.get_text(" ", strip=True)) if container else ""
        date_match = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+2026", context)
        dt = parse_date(date_match.group(0)) if date_match else datetime.min.replace(tzinfo=timezone.utc)
        meta = fetch_article_metadata(href)
        if dt == datetime.min.replace(tzinfo=timezone.utc) and meta.get("published_at"):
            dt = parse_date(meta["published_at"])

        # Never manufacture today's date when a Skyline article has no date.
        if dt == datetime.min.replace(tzinfo=timezone.utc):
            continue

        youtube_id = meta.get("youtube_id", "")
        is_video = looks_like_video(title, href, context) or bool(youtube_id)
        items.append({
            "title": title,
            "url": href,
            "date": dt.strftime("%b. %-d, %Y"),
            "published_at": dt.isoformat(),
            "description": context[:220] if context else "Skyline Sports coverage of Montana Grizzlies football.",
            "source": "Skyline Sports",
            "badge": category(title),
            "short": category(title)[:4].upper(),
            "image": meta.get("image", ""),
            "is_video": is_video,
            "youtube_id": youtube_id,
            "video_url": f"https://www.youtube.com/watch?v={youtube_id}" if youtube_id else (href if is_video else ""),
            "video_thumbnail": meta.get("video_thumbnail", "") or meta.get("image", ""),
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
        identity = url or key
        current = by_key.get(identity)
        incoming_date = parse_date(story.get("published_at") or story.get("date"))
        current_date = parse_date(current.get("published_at") or current.get("date")) if current else datetime.min.replace(tzinfo=timezone.utc)
        if current is None or incoming_date >= current_date:
            if current:
                if not story.get("image"):
                    story["image"] = current.get("image", "")
                for key in ("is_video", "youtube_id", "video_url", "video_thumbnail"):
                    if not story.get(key) and current.get(key):
                        story[key] = current.get(key)
            story["title"] = title
            story["url"] = url
            story["description"] = clean(story.get("description"))[:220]
            story["badge"] = story.get("badge") or category(title)
            story["short"] = story.get("short") or story["badge"][:4].upper()
            story["image"] = valid_image(story.get("image", ""))
            story["is_video"] = bool(story.get("is_video") or story.get("youtube_id") or looks_like_video(title, url, story.get("description", "")))
            story["youtube_id"] = clean(story.get("youtube_id", ""))
            story["video_url"] = clean(story.get("video_url", ""))
            story["video_thumbnail"] = valid_image(story.get("video_thumbnail", "")) or story.get("image", "")
            if story["youtube_id"]:
                story["video_url"] = f"https://www.youtube.com/watch?v={story['youtube_id']}"
                story["video_thumbnail"] = video_thumbnail(story["youtube_id"])
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
