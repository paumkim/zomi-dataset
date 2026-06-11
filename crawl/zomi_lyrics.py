"""
Zomi Online Lyrics scraper.

Extracts Zomi song lyrics from zomionlinelyrics.blogspot.com.
Uses Playwright to handle JavaScript-rendered content.

Usage:
    python3 crawl/zomi_lyrics.py
"""
from __future__ import annotations

import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path("data/zomi_only")
TEXT_DIR = Path("data/texts")


def get_all_post_links(page) -> list[tuple[str, str]]:
    """Extract all song post links from the blogspot homepage."""
    links: list[tuple[str, str]] = []
    seen_urls: set[str] = set()

    for a in page.query_selector_all("a"):
        href = a.get_attribute("href") or ""
        text = a.inner_text().strip()

        # Filter for blogspot post URLs
        if "/201" in href and "blogspot.com" in href:
            if href not in seen_urls and text and len(text) > 3:
                # Skip labels and archive links
                if not any(kw in href for kw in ["/search/", "#comment", "label/"]):
                    links.append((text, href))
                    seen_urls.add(href)

    return links


def extract_lyrics(page, url: str) -> str:
    """Open a song post and extract the lyric text."""
    try:
        page.goto(url, wait_until="networkidle", timeout=20000)
        time.sleep(2)

        # Get all visible text
        text = page.inner_text("body")

        # Clean and extract just the lyrics
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        # Remove boilerplate
        filtered = []
        skip_keywords = ["cookie", "privacy", "sign in", "sign up", "subscribe",
                        "comments", "share", "tweet", "pin", "email", "print",
                        "your browser does not support", "copyright", "all rights",
                        "powered by", "blogger", "home", "featured", "archive",
                        "labels", "report abuse", "no comments", "newer post",
                        "older post", "post a comment", "social plugin"]

        for l in lines:
            lower = l.lower()
            if any(kw in lower for kw in skip_keywords):
                continue
            if len(l) < 15:
                continue
            if l.isdigit():
                continue
            filtered.append(l)

        return "\n".join(filtered)

    except Exception as e:
        print(f"  Error: {e}")
        return ""


def crawl_all_lyrics(max_songs: int = 500) -> None:
    """Crawl all Zomi song lyrics from the blogspot site."""
    BASE_URL = "https://zomionlinelyrics.blogspot.com/"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0")

        # Step 1: Load homepage and get all post links
        print(f"Loading {BASE_URL}...")
        page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
        time.sleep(3)

        all_posts = get_all_post_links(page)
        print(f"Found {len(all_posts)} song posts")

        # Step 2: Check if there are more pages (older posts)
        more_link = page.query_selector("a[class*='older'], a[aria-label*='Older'], a[rel='next']")
        page_num = 1
        while more_link and len(all_posts) < max_songs:
            try:
                href = more_link.get_attribute("href")
                if href and "blogspot.com" in href:
                    print(f"Checking page {page_num + 1}...")
                    page.goto(href, wait_until="networkidle", timeout=20000)
                    time.sleep(3)
                    new_posts = get_all_post_links(page)
                    for p in new_posts:
                        if p not in all_posts:
                            all_posts.append(p)
                    more_link = page.query_selector("a[class*='older'], a[aria-label*='Older'], a[rel='next']")
                    page_num += 1
                else:
                    break
            except Exception as e:
                print(f"  Pagination error: {e}")
                break

        print(f"\nTotal song posts found: {len(all_posts)}")

        # Step 3: Visit each post and extract lyrics
        all_lyrics: list[str] = []
        for i, (title, url) in enumerate(all_posts[:max_songs]):
            print(f"[{i+1}/{min(len(all_posts), max_songs)}] {title[:60]}...", end=" ", flush=True)
            lyrics = extract_lyrics(page, url)
            if lyrics:
                all_lyrics.append(f"=== {title} ===\n{lyrics}")
                print(f"{len(lyrics)} chars")
            else:
                print("no lyrics")

            time.sleep(1)

        browser.close()

    # Step 4: Save all lyrics
    if all_lyrics:
        combined = "\n\n".join(all_lyrics)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / "zomi_lyrics_corpus.txt"
        output_path.write_text(combined, encoding="utf-8")

        # Also save individual lyrics
        TEXT_DIR.mkdir(parents=True, exist_ok=True)
        for i, lyric in enumerate(all_lyrics):
            song_file = TEXT_DIR / f"lyric_{i+1:04d}.txt"
            song_file.write_text(lyric, encoding="utf-8")

        print(f"\nSaved {len(all_lyrics)} songs ({sum(len(l) for l in all_lyrics)} chars)")
        print(f"Corpus: {output_path}")
    else:
        print("\nNo lyrics extracted")


if __name__ == "__main__":
    crawl_all_lyrics()
