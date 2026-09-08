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
    "User-Agent": "GrizHQ-NewsBot/2.0 (+https://grizhq.com)"
}

# RSS feeds are the preferred source because they are stable and inexpensive to poll.
FEEDS = [
    ("GoGriz", "https://gogriz.com/rss?path=football"),
    ("Montana Sports", "https://www.montanasports.com/index.rss"),
    ("KPAX", "https://www.kpax.com/news/rss"),
    ("NCAA FCS", "https://www.ncaa.com/news/football/fcs/rss.xml"),
    ("Missoulian", "https://missoulian.com/search/?f=rss"),
]

# Broad discovery feeds catch new stories when a publisher's own RSS feed or
# page markup changes. Google News is used only as a discovery layer; the
# updater follows each item to the original publisher before saving it.
DISCOVERY_FEEDS = [
    ("Google News", "https://news.google.com/rss/search?q=Montana+Grizzlies+football&hl=en-US&gl=US&ceid=US:en"),
    ("Google News", "https://news.google.com/rss/search?q=Montana+Griz+football&hl=en-US&gl=US&ceid=US:en"),
    ("Google News", "https://news.google.com/rss/search?q=Montana+Grizzlies+Utah+Tech&hl=en-US&gl=US&ceid=US:en"),
]

# High-value pages without dependable RSS feeds. These are parsed for article cards.
# The updater only keeps stories that are actually about Montana/Griz football.
SOURCE_PAGES = [
    ("Skyline Sports", "https://skylinesportsmt.com/"),
    ("Skyline Sports", "https://skylinesportsmt.com/category/cat-griz-football/"),
    ("Skyline Sports", "https://skylinesportsmt.com/category/press-conference/"),
    ("NBC Montana", "https://nbcmontana.com/sports"),
    ("Daily Inter Lake", "https://dailyinterlake.com/news/sports/"),
    ("Daily Inter Lake", "https://dailyinterlake.com/news/pods/"),
    ("406 MT Sports", "https://406mtsports.com/college/montana-grizzlies/"),
    ("406 MT Sports", "https://406mtsports.com/college/big-sky-conference/"),
    ("KPAX Grizzlies", "https://www.kpax.com/big-sky-conference/montana-grizzlies"),
    ("Big Sky Conference", "https://bigskyconf.com/news/"),
    ("FCS Football Central", "https://www.si.com/college/fcs/big-sky/"),
    ("FCS Football Central", "https://www.si.com/college/college-football/team/montana-grizzlies"),
    ("FCS Recruiting", "https://www.si.com/college/fcs/recruiting"),
    ("HERO Sports", "https://herosports.com/college-football/big-sky/"),
]

# Real Griz football photos used only when a story has no usable publisher image.
GRIZ_FALLBACK_IMAGES = [
    "https://dxbhsrqyrr690.cloudfront.net/sidearm.nextgen.sites/gogriz.com/images/2026/9/5/20260905_fb_v_Drake_4405_rb_AFMpW.jpg",
    "https://dxbhsrqyrr690.cloudfront.net/sidearm.nextgen.sites/gogriz.com/images/2024/9/21/_TM21627_2.jpg",
    "https://dxbhsrqyrr690.cloudfront.net/sidearm.nextgen.sites/gogriz.com/images/2026/8/30/20260829_fbvssouthernutah_0125.jpg",
    "https://dxbhsrqyrr690.cloudfront.net/sidearm.nextgen.sites/gogriz.com/images/2026/8/31/Mason_ST_POW_Web.png",
    "https://skylinesportsmt.com/wp-content/uploads/2026/08/Bobby-Kennedy-on-sideline-with-team-and-Jaylen-Johnson-780x470.jpeg",
    "https://skylinesportsmt.com/wp-content/uploads/2026/04/Brooks-Nuanez-Cat-Griz-2025-Eli-Gillman-solo-scaled.jpeg",
]

def griz_fallback_image(story, index=0):
    seed = f"{story.get('url','')}|{story.get('title','')}"
    slot = (sum(seed.encode("utf-8")) + index) % len(GRIZ_FALLBACK_IMAGES)
    return GRIZ_FALLBACK_IMAGES[slot]

KNOWN_IMAGES = {
    "https://www.montanasports.com/college/montana-grizzlies/no-3-montana-blows-past-drake-as-eli-gillman-rewrites-rushing-td-record": "https://ewscripps.brightspotcdn.com/dims4/default/67070b8/2147483647/strip/true/crop/3977x2237+0+0/resize/1280x720!/quality/90/?url=http://ewscripps-brightspot.s3.amazonaws.com/31/52/14a9c88541e9942044eff39e1f84/20260905-fbvsdrake-048.jpg",
    "https://gogriz.com/news/2026/9/5/football-gillman-sets-records-as-griz-roll-past-bulldogs-45-10": "https://dxbhsrqyrr690.cloudfront.net/sidearm.nextgen.sites/gogriz.com/images/2026/9/5/20260905_fb_v_Drake_4405_rb_AFMpW.jpg",
    "https://dailyinterlake.com/news/2026/sep/06/give-gillman-the-crown-griz-ride-rbs-4-touchdowns-to-win-pver-drake/": "https://dxbhsrqyrr690.cloudfront.net/sidearm.nextgen.sites/gogriz.com/images/2026/9/5/20260905_fb_v_Drake_4405_rb_AFMpW.jpg",
    "https://skylinesportsmt.com/gillman-breaks-record-as-griz-overcome-penalties-to-cruise-past-drake-for-second-straight-win/": "https://skylinesportsmt.com/wp-content/uploads/2026/08/Bobby-Kennedy-on-sideline-with-team-and-Jaylen-Johnson-780x470.jpeg",
}

GRIZ_TERMS = (
    "montana grizzlies", "montana griz", "griz football", "griz", "gillman",
    "bobby kennedy", "keali'i ah yat", "kealii ah yat", "landon ransom-goelz",
    "brooks davis", "washington-grizzly", "washington grizzly", "grizzly stadium",
    "montana football", "university of montana football", "gogriz"
)
EXCLUDE_TERMS = (
    "montana state", "bobcats", "bobcat", "msu football", "bozeman",
    "cats and griz"
)

IMAGE_CACHE = {}
REDIRECT_CACHE = {}
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
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d",
        "%B %d, %Y", "%b %d, %Y", "%B %d, %Y %I:%M %p", "%b %d, %Y %I:%M %p",
        "%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M %z",
        "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %I:%M %p"
    ):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
        except Exception:
            continue
    return datetime.min.replace(tzinfo=timezone.utc)


def is_griz_story(title, description=""):
    text = f"{title} {description}".lower()
    if any(term in text for term in EXCLUDE_TERMS):
        strong = (
            "montana grizzlies", "montana griz", "griz football", "eli gillman",
            "bobby kennedy", "keali'i ah yat", "kealii ah yat", "montana football"
        )
        return any(term in text for term in strong)
    return any(term in text for term in GRIZ_TERMS)


def category(title):
    t = title.lower()
    if any(x in t for x in ("press conference", "post-game", "postgame", "interview", "podcast", "inside the fcs", "watch –", "watch -")):
        return "INSIDER"
    if any(x in t for x in ("commit", "commits", "recruit", "recruiting", "offer", "portal", "transfer")):
        return "RECRUITING"
    if any(x in t for x in ("utah tech", "trailblazers", "opponent", "byu")):
        return "OPPONENT"
    if any(x in t for x in ("preview", "vs.", "vs ", "against", "look to", "what you should wear", "game day")):
        return "GAME DAY"
    if any(x in t for x in ("recap", "roll past", "outlast", "beats", "beat ", "victory", "wins", "win over", "defeats", "defeat")):
        return "GAME STORY"
    if any(x in t for x in ("player of the week", "award", "named", "honor", "all-big sky")):
        return "HONOR"
    if any(x in t for x in ("analysis", "numbers", "inside", "breakdown", "film", "keys to")):
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
    candidates = []
    for node in item.iter():
        tag = node.tag.split("}")[-1].lower() if isinstance(node.tag, str) else ""
        if tag in ("content", "thumbnail", "enclosure"):
            raw = node.attrib.get("url") or node.attrib.get("href") or ""
            if raw:
                candidates.append(raw)
    for raw in candidates:
        image = valid_image(urljoin(base_url, raw))
        if image:
            return image
    return ""


def fetch_article_metadata(url):
    url = normalize_url(url)
    if not url:
        return {"image": "", "published_at": "", "youtube_id": "", "video_thumbnail": ""}
    if url in IMAGE_CACHE:
        return IMAGE_CACHE[url]
    result = {"image": "", "published_at": "", "youtube_id": "", "video_thumbnail": ""}
    try:
        response = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        result["youtube_id"] = extract_youtube_id(response.text)
        if result["youtube_id"]:
            result["video_thumbnail"] = video_thumbnail(result["youtube_id"])
        for attrs in ({"property": "og:image"}, {"name": "twitter:image"}, {"itemprop": "image"}):
            node = soup.find("meta", attrs=attrs)
            if node and node.get("content"):
                result["image"] = valid_image(urljoin(response.url, node["content"]))
                if result["image"]:
                    break
        if not result["image"]:
            for node in soup.select("article img, main img")[:8]:
                src = node.get("src") or node.get("data-src") or node.get("data-lazy-src")
                image = valid_image(urljoin(response.url, src or ""))
                if image:
                    result["image"] = image
                    break
        # Publishers expose publication time in several different ways.
        date_value = ""
        date_node = (
            soup.find("meta", attrs={"property": "article:published_time"})
            or soup.find("meta", attrs={"property": "article:published"})
            or soup.find("meta", attrs={"name": "date"})
            or soup.find("meta", attrs={"name": "pubdate"})
            or soup.find("meta", attrs={"itemprop": "datePublished"})
        )
        if date_node:
            date_value = date_node.get("content") or date_node.get("datetime") or date_node.get_text(" ", strip=True)
        if not date_value:
            for node in soup.select('time[datetime], time[itemprop="datePublished"], [itemprop="datePublished"]')[:8]:
                date_value = node.get("datetime") or node.get("content") or node.get_text(" ", strip=True)
                if date_value:
                    break
        if not date_value:
            # JSON-LD is common on modern publisher pages.
            for node in soup.find_all("script", attrs={"type": "application/ld+json"})[:12]:
                try:
                    raw = json.loads(node.string or node.get_text() or "{}")
                    candidates = raw if isinstance(raw, list) else [raw]
                    for obj in candidates:
                        if isinstance(obj, dict):
                            if isinstance(obj.get("@graph"), list):
                                candidates.extend(obj["@graph"])
                            for key in ("datePublished", "dateCreated"):
                                if obj.get(key):
                                    date_value = obj[key]
                                    break
                        if date_value:
                            break
                    if date_value:
                        break
                except Exception:
                    continue
        if date_value:
            result["published_at"] = clean(str(date_value))
    except Exception as exc:
        print(f"Metadata fetch failed for {url}: {exc}")
    IMAGE_CACHE[url] = result
    return result


def make_story(title, link, description, source, published_value="", image="", is_video=False, video_url=""):
    title = clean(title)
    link = normalize_url(link)
    description = clean(description)
    if not title or not link or not is_griz_story(title, description):
        return None
    dt = parse_date(published_value)
    meta = fetch_article_metadata(link)
    image = valid_image(image) or meta.get("image", "") or KNOWN_IMAGES.get(link, "")
    youtube_id = meta.get("youtube_id", "")
    video_flag = is_video or looks_like_video(title, link, description) or bool(youtube_id)
    if dt == datetime.min.replace(tzinfo=timezone.utc) and meta.get("published_at"):
        dt = parse_date(meta["published_at"])
    return {
        "title": title,
        "url": link,
        "date": dt.strftime("%b. %-d, %Y") if dt != datetime.min.replace(tzinfo=timezone.utc) else "",
        "published_at": dt.isoformat() if dt != datetime.min.replace(tzinfo=timezone.utc) else "",
        "description": description[:240] or "Latest Montana football coverage.",
        "source": source,
        "badge": category(title),
        "short": category(title)[:6].upper(),
        "image": image,
        "is_video": video_flag,
        "youtube_id": youtube_id,
        "video_url": f"https://www.youtube.com/watch?v={youtube_id}" if youtube_id else (video_url or (link if video_flag else "")),
        "video_thumbnail": meta.get("video_thumbnail", "") or image,
    }


def resolve_publisher_url(url):
    """Follow a Google News redirect and return the original publisher URL."""
    url = normalize_url(url)
    if not url or "news.google.com" not in urlparse(url).netloc.lower():
        return url
    if url in REDIRECT_CACHE:
        return REDIRECT_CACHE[url]
    try:
        response = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        final_url = normalize_url(response.url)
        if "news.google.com" not in urlparse(final_url).netloc.lower():
            REDIRECT_CACHE[url] = final_url
            return final_url
    except Exception as exc:
        print(f"Google News redirect failed: {exc}")
    REDIRECT_CACHE[url] = ""
    return ""


def parse_google_news_rss(url):
    response = requests.get(url, headers=HEADERS, timeout=25)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    items = []
    for item in root.findall(".//item")[:30]:
        title = clean(item.findtext("title") or "")
        raw_link = clean(item.findtext("link") or "")
        link = resolve_publisher_url(raw_link)
        if not title or not link:
            continue
        pub = clean(item.findtext("pubDate") or "")
        desc = BeautifulSoup(clean(item.findtext("description") or ""), "html.parser").get_text(" ", strip=True)
        source_node = item.find("source")
        publisher = clean(source_node.text if source_node is not None else "") or "News"
        story = make_story(title, link, desc, publisher, pub, "")
        if story:
            items.append(story)
    return items


def parse_rss(source, url):
    response = requests.get(url, headers=HEADERS, timeout=25)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    items = []
    nodes = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    for item in nodes[:40]:
        title = clean(item.findtext("title") or item.findtext("{http://www.w3.org/2005/Atom}title"))
        link = clean(item.findtext("link") or "")
        if not link:
            atom_link = item.find("{http://www.w3.org/2005/Atom}link")
            link = clean(atom_link.attrib.get("href", "") if atom_link is not None else "")
        pub = clean(item.findtext("pubDate") or item.findtext("published") or item.findtext("updated") or "")
        desc = BeautifulSoup(clean(item.findtext("description") or item.findtext("summary") or ""), "html.parser").get_text(" ", strip=True)
        story = make_story(title, link, desc, source, pub, image_from_rss_item(item, link))
        if story:
            items.append(story)
    return items


def parse_listing_page(source, url, limit=18):
    response = requests.get(url, headers=HEADERS, timeout=25)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    items = []
    seen = set()
    selectors = [
        "article a[href]", ".article a[href]", ".story a[href]", ".card a[href]",
        "main a[href]", "a[href]"
    ]
    for selector in selectors:
        for a in soup.select(selector):
            href = urljoin(response.url, a.get("href", ""))
            title = clean(a.get_text(" ", strip=True))
            if not title or len(title) < 16 or href in seen:
                continue
            if urlparse(href).netloc and urlparse(href).netloc not in urlparse(response.url).netloc:
                continue
            low = href.lower()
            if any(x in low for x in ("/category/", "/tag/", "/author/", "/page/", "javascript:")):
                continue
            container = a.find_parent(["article", "div", "li", "section"])
            context = clean(container.get_text(" ", strip=True)) if container else title
            # Avoid navigation links and unrelated site clutter.
            if not is_griz_story(title, context):
                continue
            meta = fetch_article_metadata(href)
            dt = parse_date(meta.get("published_at", ""))
            if dt == datetime.min.replace(tzinfo=timezone.utc):
                # Search nearby text for a conventional 2026 date.
                match = re.search(r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+2026", context)
                if match:
                    dt = parse_date(match.group(0))
            if dt == datetime.min.replace(tzinfo=timezone.utc):
                continue
            story = make_story(
                title, href, context[:500], source,
                dt.isoformat(), meta.get("image", ""),
                looks_like_video(title, href, context)
            )
            if story:
                items.append(story)
                seen.add(href)
            if len(items) >= limit:
                return items
        if items:
            break
    return items


def load_existing():
    if not NEWS_FILE.exists():
        return []
    try:
        data = json.loads(NEWS_FILE.read_text(encoding="utf-8"))
        stories = data.get("stories", []) if isinstance(data, dict) else []
        return [s for s in stories if "news.google.com" not in str(s.get("url", "")).lower() and str(s.get("source", "")).lower() != "google news"]
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
        # URL is primary identity; normalized title catches syndicated duplicates.
        title_key = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
        identity = url or title_key
        current = by_key.get(identity)
        incoming_date = parse_date(story.get("published_at") or story.get("date"))
        current_date = parse_date(current.get("published_at") or current.get("date")) if current else datetime.min.replace(tzinfo=timezone.utc)
        if current is None or incoming_date >= current_date:
            if current:
                for key in ("image", "is_video", "youtube_id", "video_url", "video_thumbnail", "description"):
                    if not story.get(key) and current.get(key):
                        story[key] = current[key]
            story["title"] = title
            story["url"] = url
            story["description"] = clean(story.get("description"))[:240]
            story["badge"] = story.get("badge") or category(title)
            story["short"] = story.get("short") or story["badge"][:6].upper()
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
    # Keep a large rolling library so the site has fresh headlines even between big news days.
    for i, story in enumerate(result):
        if not valid_image(story.get("image", "")):
            story["image"] = griz_fallback_image(story, i)
            story["image_fallback"] = True
        else:
            story.pop("image_fallback", None)
        if not valid_image(story.get("video_thumbnail", "")):
            story["video_thumbnail"] = story["image"]
    return result[:100]


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

    for source, url in DISCOVERY_FEEDS:
        try:
            items = parse_google_news_rss(url)
            print(f"{source} discovery ({url.split('q=', 1)[-1].split('&', 1)[0]}): {len(items)} Griz stories")
            fetched.extend(items)
        except Exception as exc:
            print(f"{source} discovery failed: {exc}")

    for source, url in SOURCE_PAGES:
        try:
            items = parse_listing_page(source, url)
            print(f"{source}: {len(items)} Griz stories")
            fetched.extend(items)
        except Exception as exc:
            print(f"{source} page failed: {exc}")

    fetched = [s for s in fetched if "news.google.com" not in str(s.get("url", "")).lower() and str(s.get("source", "")).lower() != "google news"]
    merged = dedupe_and_sort(fetched + existing)
    if not merged:
        print("No stories collected; leaving news.json unchanged.")
        return

    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": "Automated Griz HQ news hub",
        "story_count": len(merged),
        "sources": sorted(set(str(s.get("source", "")).strip() for s in merged if s.get("source"))),
        "stories": merged,
    }
    NEWS_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(merged)} stories to news.json from {len(payload['sources'])} sources.")


if __name__ == "__main__":
    main()
