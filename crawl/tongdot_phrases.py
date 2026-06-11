"""
TongDot Phrases scraper — extracts full Zomi sentences across all dialects.

The phrases page has English sentences translated into Tedim, Falam, Hakha,
Sizang, Mizo, and Matu dialects. This scraper extracts and saves them all.

Usage:
    python3 crawl/tongdot_phrases.py
"""
from __future__ import annotations

import urllib.request
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

PHRASES_URL = "https://www.tongdot.com/site/page?view=phrases"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

OUTPUT_PATH = Path("data/texts/tongdot_phrases.txt")


def fetch_phrases() -> list[dict[str, str]]:
    """Fetch all phrases from TongDot and return as Zomi sentences."""
    req = urllib.request.Request(PHRASES_URL, headers={"User-Agent": USER_AGENT})
    html = urllib.request.urlopen(req, timeout=15).read()
    soup = BeautifulSoup(html, "html.parser")

    phrases: list[dict[str, str]] = []

    # Find all tables on the page
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            texts = [c.get_text(strip=True) for c in cells]

            if len(texts) < 2:
                continue

            english = texts[0].strip()
            if not english or len(english) < 2:
                continue

            # Skip header rows
            if english.lower() in ("english", "basic", "numbers", "days", ""):
                continue

            # Extract Zomi from each dialect column (indices 1-5)
            for col_idx, dialect_name in [(1, "tedim"), (2, "falam"),
                                            (3, "hakha"), (4, "sizang"),
                                            (5, "mizo"), (6, "matu")]:
                if col_idx < len(texts):
                    zomi = texts[col_idx].strip()
                    if zomi and len(zomi) > 1 and zomi != english:
                        # Skip pure numbers and punctuation
                        if not zomi.replace(".", "").replace(",", "").isdigit():
                            phrases.append({
                                "english": english,
                                "zomi": zomi,
                                "dialect": dialect_name,
                                "source": "tongdot.com/phrases",
                            })

    # Deduplicate
    seen = set()
    unique_phrases = []
    for p in phrases:
        key = (p["english"], p["zomi"], p["dialect"])
        if key not in seen:
            seen.add(key)
            unique_phrases.append(p)

    return unique_phrases


def save_phrases(phrases: list[dict[str, str]]) -> int:
    """Save phrases as plain text Zomi sentences."""
    zomi_only = []
    for p in phrases:
        zomi = p["zomi"]
        # Clean up
        zomi = zomi.strip(" .").strip()
        if zomi and len(zomi) > 1:
            zomi_only.append(f"{zomi}.")

    # Also add dialect-paired versions
    paired = []
    for p in phrases:
        english = p["english"]
        zomi = p["zomi"]
        if zomi and english:
            paired.append(f"EN: {english} | ZO: {zomi}")

    combined = "# Zomi Phrases from TongDot\n\n"
    combined += "## Zomi-Only\n"
    combined += "\n".join(zomi_only)
    combined += "\n\n## English-Zomi Pairs\n"
    combined += "\n".join(paired)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(combined, encoding="utf-8")
    return len(zomi_only)


def main():
    print(f"Fetching phrases from {PHRASES_URL}...")
    phrases = fetch_phrases()
    zomi_count = save_phrases(phrases)
    print(f"Found {len(phrases)} phrase translations across all dialects")
    print(f"Saved {zomi_count} unique Zomi sentences to {OUTPUT_PATH}")

    # Summary by dialect
    from collections import Counter
    dialects = Counter(p["dialect"] for p in phrases)
    print(f"\nBy dialect:")
    for dialect, count in dialects.most_common():
        print(f"  {dialect}: {count}")

    # Show examples
    print(f"\nSample Zomi sentences:")
    seen_eng = set()
    for p in phrases:
        if p["english"] not in seen_eng:
            seen_eng.add(p["english"])
            for d in ["tedim", "falam", "hakha"]:
                match = [q for q in phrases if q["english"] == p["english"] and q["dialect"] == d]
                if match:
                    print(f"  [{d}] {p['english']} → {match[0]['zomi']}")
                    break


if __name__ == "__main__":
    main()
