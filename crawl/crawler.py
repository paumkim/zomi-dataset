"""
Multi-site Zomi web crawler.

Crawls known Zomi-language websites, extracts text, detects Zomi language,
and saves clean Zomi content to the dataset.

Sites supported:
  - tongdot.com           (dictionary - autocomplete API)
  - zomidictionary.com    (dictionary)
  - zomilaisiangtho.com   (Zomi Bible)
  - zomiworshipcollective.com/lyrics/ (worship lyrics)
  - zomionlinelyrics.blogspot.com     (song lyrics)
  - zomidaily.com         (news)
  - zomielibrary.com      (library)
  - scribd.com            (documents - PDF extraction)
  - academia.edu          (academic papers)
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import urllib.parse
import urllib.robotparser
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from config import (
    CRAWL_DELAY, USER_AGENT, DATA_RAW, DATA_TEXTS, DATA_ZOMI,
    ZOMI_THRESHOLD, OTHER_THRESHOLD, MIN_PARAGRAPH_LENGTH,
)

# ── Visited URL tracker (prevents re-downloading same pages) ──

VISITED_FILE = Path("data/visited_urls.json")


def load_visited() -> set[str]:
    if VISITED_FILE.exists():
        try:
            return set(json.loads(VISITED_FILE.read_text()))
        except (json.JSONDecodeError, OSError):
            pass
    return set()


def save_visited(urls: set[str]) -> None:
    VISITED_FILE.parent.mkdir(parents=True, exist_ok=True)
    VISITED_FILE.write_text(json.dumps(sorted(urls), indent=2))


def is_visited(url: str, visited: set[str]) -> bool:
    return url.rstrip("/") in visited


def mark_visited(url: str, visited: set[str]) -> None:
    visited.add(url.rstrip("/"))


# ── Site definitions ──

SITES = [
    {
        "name": "tongdot",
        "seed_url": "https://www.tongdot.com/",
        "type": "dictionary",
        "handler": "autocomplete",
        "delay": 1.5,
    },
    {
        "name": "zomidictionary",
        "seed_url": "https://www.zomidictionary.com/",
        "type": "dictionary",
        "handler": "html",
        "delay": 2.0,
    },
    {
        "name": "zomilaisiangtho",
        "seed_url": "https://zomilaisiangtho.com/",
        "type": "bible",
        "handler": "html",
        "delay": 1.5,
    },
    {
        "name": "zomiworship",
        "seed_url": "https://zomiworshipcollective.com/lyrics/",
        "type": "lyrics",
        "handler": "html",
        "delay": 1.5,
    },
    {
        "name": "zomilyrics",
        "seed_url": "https://zomionlinelyrics.blogspot.com/",
        "type": "lyrics",
        "handler": "blogspot",
        "delay": 2.0,
    },
    {
        "name": "zomidaily",
        "seed_url": "https://zomidaily.com/",
        "type": "news",
        "handler": "html",
        "delay": 2.0,
    },
    {
        "name": "zomielibrary",
        "seed_url": "https://zomielibrary.com/",
        "type": "library",
        "handler": "html",
        "delay": 2.0,
    },
]


def fetch_page(url: str, timeout: int = 15) -> str | None:
    """Fetch a web page and return its HTML content."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
        logging.warning("Failed to fetch %s: %s", url, e)
        return None


# ── HTML Text Extraction ──

def extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML using BeautifulSoup."""
    soup = BeautifulSoup(html, 'html.parser')

    # Remove non-content elements
    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'noscript',
                     'iframe', 'svg', 'form', 'input', 'button', 'select']):
        tag.decompose()

    # Get text with paragraph separation
    text = soup.get_text(separator='\n')

    # Clean up whitespace
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # Filter out garbage lines
    skip_keywords = ['skip to main', 'log in', 'sign up', 'search', 'menu',
                     'cookie', 'privacy', 'terms', 'copyright',
                     'all rights reserved', 'loading', 'share', 'save',
                     'buy me a coffee', 'subscribe', 'newsletter',
                     'sponsored', 'advertisement', 'click here']

    clean_lines = []
    for line in lines:
        lower = line.lower()
        if any(kw in lower for kw in skip_keywords):
            continue
        if len(line) < 15:
            continue
        clean_lines.append(line)

    return '\n'.join(clean_lines)


# ── Zomi Language Detection ──

def load_zomi_profile() -> dict:
    """Load the Zomi character bigram profile."""
    profile_path = Path("detect/profiles/zomi_bigrams.json")
    if not profile_path.exists():
        return {"bigrams": {}, "total_chars": 0}
    return json.loads(profile_path.read_text())


def score_text(text: str, profile: dict) -> dict[str, float]:
    """Score text against language profiles.

    Returns scores for Zomi, English, and other languages.
    Score is 0.0 to 1.0 — higher means more likely.
    """
    import json

    bigram_profile = profile.get("bigrams", {})

    # Extract bigrams from input text
    text_bigrams: dict[str, int] = {}
    clean = text.lower()
    for i in range(len(clean) - 1):
        bg = clean[i:i+2]
        if bg.isalpha() or "'" in bg:
            text_bigrams[bg] = text_bigrams.get(bg, 0) + 1

    if not text_bigrams:
        return {"zomi": 0.0, "english": 0.0, "other": 1.0}

    # Score against Zomi profile
    total = sum(text_bigrams.values())
    zomi_score = 0.0
    for bg, count in text_bigrams.items():
        if bg in bigram_profile:
            zomi_score += count * bigram_profile[bg]
    zomi_score = min(1.0, zomi_score * 10)  # Scale up

    # Rough English detection: check for common English words
    english_words = {"the", "and", "for", "are", "but", "not", "you", "all",
                     "can", "had", "her", "was", "one", "our", "out", "has",
                     "have", "been", "some", "them", "than", "what", "when",
                     "which", "their", "there", "would", "could", "should"}
    words = set(clean.split())
    english_overlap = len(words & english_words)
    english_score = min(1.0, english_overlap / max(len(words), 1) * 5)

    # Check for Zomi-specific patterns
    zomi_patterns = ["hi", "a ", "in ", "leh", "na ", "tawh", "sung", "bang",
                     "ciang", "khin", "ding", "mah", "zong", "maw?", "lo "]
    pattern_matches = sum(1 for p in zomi_patterns if p in clean)
    pattern_score = min(1.0, pattern_matches / 3)

    # Combined Zomi score
    zomi_score = max(zomi_score, pattern_score)

    return {"zomi": zomi_score, "english": english_score, "other": max(0, 1 - zomi_score - english_score)}


def is_zomi_text(text: str, profile: dict) -> bool:
    """Check if a paragraph of text is likely Zomi."""
    if len(text) < MIN_PARAGRAPH_LENGTH:
        return False

    scores = score_text(text, profile)
    return scores["zomi"] >= ZOMI_THRESHOLD and scores["english"] < OTHER_THRESHOLD


# ── Page Discovery ──

SKIP_EXTENSIONS = {'.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg',
                    '.ico', '.woff', '.woff2', '.ttf', '.eot', '.mp3',
                    '.mp4', '.pdf', '.zip', '.tar', '.gz'}


def discover_links(html: str, base_url: str, site_name: str) -> list[str]:
    """Extract all internal links from HTML for crawling."""
    links = set()
    base_domain = urllib.parse.urlparse(base_url).netloc

    for match in re.finditer(r'href=["\'](.*?)["\']', html, re.IGNORECASE):
        url = match.group(1)
        if not url or url.startswith("#") or url.startswith("javascript:"):
            continue

        # Skip non-HTML files
        ext = urllib.parse.urlparse(url).path.split('.')[-1].lower() if '.' in url else ''
        if f'.{ext}' in SKIP_EXTENSIONS:
            continue

        # Resolve relative URLs
        absolute = urllib.parse.urljoin(base_url, url)

        # Only keep links to the same domain
        domain = urllib.parse.urlparse(absolute).netloc
        if domain == base_domain or domain.endswith("." + base_domain):
            # Remove anchors and normalize
            absolute = urllib.parse.urldefrag(absolute)[0]
            # Skip file extensions
            path = urllib.parse.urlparse(absolute).path
            if any(path.endswith(ext) for ext in SKIP_EXTENSIONS):
                continue
            if absolute not in links:
                links.add(absolute)

    return sorted(links)[:200]  # Max 200 pages per site


# ── Crawlers for Specific Sites ──

def crawl_tongdot_autocomplete() -> list[dict]:
    """Crawl TongDot dictionary via autocomplete API (27K+ entries)."""
    from crawl.tongdot import crawl_all, discover_all_words
    print("\n[TongDot] Phase 1: Discovering words via autocomplete...")
    words = discover_all_words()
    print(f"[TongDot] Found {len(words)} words")
    print("[TongDot] Phase 2: Fetching definitions...")
    return crawl_all(discovered_words=words)


def crawl_generic(site: dict, max_pages: int = 100) -> int:
    """Generic crawler for HTML-based Zomi sites."""
    name = site["name"]
    seed = site["seed_url"]
    delay = site.get("delay", CRAWL_DELAY)

    print(f"\n[{name}] Crawling {seed}...")
    profile = load_zomi_profile()
    visited_global = load_visited()

    visited: set[str] = set()
    to_visit: list[str] = [seed]
    zomi_texts: list[str] = []
    total_saved = 0
    skipped = 0

    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)
        if url in visited:
            continue
        if is_visited(url, visited_global):
            visited.add(url)
            skipped += 1
            continue
        visited.add(url)

        html = fetch_page(url)
        if not html:
            continue

        # Extract text
        text = extract_text_from_html(html)

        # Check if it contains Zomi
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        zomi_paragraphs = [p for p in paragraphs if is_zomi_text(p, profile)]

        if zomi_paragraphs:
            combined = '\n\n'.join(zomi_paragraphs)
            zomi_texts.append(f"=== Source: {url} ===\n{combined}")

            # Save incrementally
            output_path = DATA_TEXTS / f"{name}_{len(visited):04d}.txt"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(combined, encoding="utf-8")
            mark_visited(url, visited_global)
            total_saved += 1
            print(f"[{name}] ✓ Saved {len(combined)} chars from {url}")

        # Save visited list periodically
        if len(visited_global) % 10 == 0:
            save_visited(visited_global)

        # Discover more links
        new_links = discover_links(html, url, name)
        for link in new_links:
            if link not in visited and link not in to_visit:
                # Prioritize links that look like content
                if any(kw in link.lower() for kw in ['article', 'post', 'lyric',
                                                      'song', 'book', 'chapter',
                                                      'page', 'content', '/202', '/20']):
                    to_visit.insert(0, link)
                else:
                    to_visit.append(link)

        time.sleep(delay)

    # Save visited URLs
    save_visited(visited_global)

    # Save combined Zomi texts
    if zomi_texts:
        combined_path = DATA_ZOMI / f"crawled_{name}.txt"
        combined_path.parent.mkdir(parents=True, exist_ok=True)
        combined_path.write_text('\n\n'.join(zomi_texts), encoding="utf-8")

    print(f"[{name}] Done. Visited {len(visited)} pages ({skipped} skipped), saved {total_saved} Zomi paragraphs.")
    return total_saved


def crawl_blogspot(site: dict, max_pages: int = 100) -> int:
    """Crawler specifically for Blogspot sites (zomionlinelyrics)."""
    name = site["name"]
    seed = site["seed_url"]
    delay = site.get("delay", CRAWL_DELAY)

    print(f"\n[{name}] Crawling Blogspot {seed}...")
    profile = load_zomi_profile()

    visited: set[str] = set()
    visited_global = load_visited()
    zomi_texts: list[str] = []
    total_saved = 0

    # Blogspot often uses /p/ for posts
    patterns = [r'/p/', r'/20\d\d/\d\d/', r'.blogspot.com/']

    def is_content_url(url: str) -> bool:
        return any(re.search(p, url) for p in patterns)

    urls_to_check = [seed]
    # First pass: collect post URLs from homepage and archive
    html = fetch_page(seed)
    if html:
        for match in re.finditer(r'href=["\'](https?://[^"\']+)["\']', html):
            url = urllib.parse.urldefrag(match.group(1))[0]
            if 'zomionlinelyrics' in url and url not in urls_to_check:
                urls_to_check.append(url)

    for url in urls_to_check[:max_pages]:
        if url in visited:
            continue
        if is_visited(url, visited_global):
            print(f"[{name}] ⏭ Skipping already-visited: {url[:80]}")
            visited.add(url)
            continue
        visited.add(url)

        html = fetch_page(url)
        if not html:
            continue

        text = extract_text_from_html(html)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        profile = load_zomi_profile()
        zomi_paragraphs = [p for p in paragraphs if is_zomi_text(p, profile)]

        if zomi_paragraphs:
            combined = '\n\n'.join(zomi_paragraphs)
            zomi_texts.append(f"=== Source: {url} ===\n{combined}")
            output_path = DATA_TEXTS / f"{name}_{len(visited):04d}.txt"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(combined, encoding="utf-8")
            mark_visited(url, visited_global)
            total_saved += 1
            print(f"[{name}] ✓ Saved {len(combined)} chars from {url}")

        time.sleep(delay)

    save_visited(visited_global)

    if zomi_texts:
        combined_path = DATA_ZOMI / f"crawled_{name}.txt"
        combined_path.parent.mkdir(parents=True, exist_ok=True)
        combined_path.write_text('\n\n'.join(zomi_texts), encoding="utf-8")

    print(f"[{name}] Done. Saved {total_saved} pages.")
    return total_saved


# ── Main Crawler Entry ──

def crawl_site(name: str | None = None) -> None:
    """Crawl Zomi-language websites."""
    sites_to_crawl = [s for s in SITES if name is None or s["name"] == name]

    if not sites_to_crawl:
        print(f"Unknown site: {name}")
        print(f"Available: {', '.join(s['name'] for s in SITES)}")
        return

    for site in sites_to_crawl:
        handler = site.get("handler", "html")
        try:
            if handler == "autocomplete":
                entries = crawl_tongdot_autocomplete()
                print(f"[{site['name']}] {len(entries)} dictionary entries collected")
            elif handler == "blogspot":
                crawl_blogspot(site)
            else:
                crawl_generic(site)
        except Exception as e:
            print(f"[{site['name']}] Error: {e}")
            import traceback
            traceback.print_exc()


def crawl_all() -> dict[str, int]:
    """Crawl all configured Zomi websites."""
    results: dict[str, int] = {}
    for site in SITES:
        crawl_site(site["name"])
        results[site["name"]] = 1
    return results
