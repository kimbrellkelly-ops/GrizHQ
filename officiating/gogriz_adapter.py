#!/usr/bin/env python3
"""
Griz HQ Officiating Intelligence — GoGriz source adapter v0.1

Purpose:
  Fetch a public GoGriz football box-score page, convert its server-rendered
  HTML into stable line-oriented text, and pass that source snapshot into the
  existing v0.2 officiating normalizer.

Safety philosophy:
  - Only allow gogriz.com hosts by default.
  - Preserve the fetched source snapshot alongside normalized output.
  - Do not publish or commit records from this adapter.
  - Fail closed on HTTP/HTML errors.
  - Missing fields remain NULL in the downstream parser.

This adapter deliberately does not attempt to "fix" source data. The
normalizer remains responsible for parsing and validation/reconciliation.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from officiating_ingest import parse_game


ALLOWED_HOSTS = {"gogriz.com", "www.gogriz.com"}
DEFAULT_TIMEOUT = 30


class VisibleTextParser(HTMLParser):
    """Turn server-rendered HTML into useful, line-oriented visible text."""

    BLOCK_TAGS = {
        "address", "article", "aside", "blockquote", "br", "caption",
        "dd", "div", "dl", "dt", "fieldset", "figcaption", "figure",
        "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6",
        "header", "hr", "li", "main", "nav", "ol", "p", "pre",
        "section", "table", "tbody", "td", "tfoot", "th", "thead",
        "tr", "ul"
    }
    SKIP_TAGS = {"script", "style", "noscript", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth == 0 and tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_startendtag(self, tag: str, attrs) -> None:
        if self.skip_depth == 0:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            if self.skip_depth:
                self.skip_depth -= 1
            return
        if self.skip_depth == 0 and tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_depth == 0:
            self.parts.append(html.unescape(data))

    def text(self) -> str:
        raw = "".join(self.parts).replace("\xa0", " ")
        lines = []
        for line in raw.splitlines():
            line = re.sub(r"\s+", " ", line).strip()
            if line:
                lines.append(line)
        return "\n".join(lines) + "\n"


def validate_url(url: str) -> None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in ALLOWED_HOSTS:
        raise ValueError("Only HTTPS GoGriz URLs on gogriz.com are permitted.")


def fetch_html(url: str, timeout: int = DEFAULT_TIMEOUT) -> bytes:
    validate_url(url)
    request = Request(
        url,
        headers={
            "User-Agent": "GrizHQ-Officiating-Research/0.1 (+public-source-ingestion)"
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get_content_type()
            if content_type not in {"text/html", "application/xhtml+xml"}:
                raise ValueError(f"Unexpected GoGriz content type: {content_type}")
            return response.read()
    except HTTPError as exc:
        raise RuntimeError(f"GoGriz returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Unable to fetch GoGriz: {exc.reason}") from exc


def html_to_text(raw_html: bytes) -> str:
    parser = VisibleTextParser()
    parser.feed(raw_html.decode("utf-8", errors="replace"))
    parser.close()
    text = parser.text()
    if not text.strip():
        raise ValueError("GoGriz HTML produced no visible text.")
    return text


def ingest_url(url: str, game_id: str, snapshot_path: str | None = None) -> dict:
    raw_html = fetch_html(url)
    source_text = html_to_text(raw_html)
    result = parse_game(source_text, game_id)
    result["source"] = {
        "source_type": "GoGriz box score",
        "url": url,
        "adapter_version": "0.1",
        "content_type": "text/html",
        "source_text_lines": len(source_text.splitlines()),
    }
    if snapshot_path:
        Path(snapshot_path).write_text(source_text, encoding="utf-8")
        result["source"]["text_snapshot"] = snapshot_path
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest a GoGriz football box score")
    parser.add_argument("url")
    parser.add_argument("game_id")
    parser.add_argument("output_json")
    parser.add_argument("--snapshot", help="Optional path for normalized source-text snapshot")
    args = parser.parse_args()

    try:
        result = ingest_url(args.url, args.game_id, args.snapshot)
        Path(args.output_json).write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result["validation"], indent=2))
        return 0
    except Exception as exc:
        print(f"INGEST FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
