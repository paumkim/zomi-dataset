"""
TongDot.com dictionary crawler.

Scrapes all 27,755 English→Zomi word pairs from the TongDot online dictionary.
Uses the site's autocomplete API to discover words, then fetches each definition.
"""
from __future__ import annotations

import json
import re
import time
import urllib.request
import urllib.error
from pathlib import Path

from config import CRAWL_DELAY, USER_AGENT, DATA_DATASET


TONGDOT_BASE = "https://www.tongdot.com"
AUTOCOMPLETE_URL = f"{TONGDOT_BASE}/word/completion"
SEARCH_URL = f"{TONGDOT_BASE}/site/index"


def fetch_autocomplete(term: str) -> list[str]:
    """Fetch autocomplete suggestions for a given term."""
    url = f"{AUTOCOMPLETE_URL}?term={urllib.request.quote(term)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data if isinstance(data, list) else []
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        print(f"  [WARN] Autocomplete failed for '{term}': {e}")
        return []


def fetch_word(word: str) -> dict | None:
    """Fetch a single word definition from TongDot."""
    url = f"{SEARCH_URL}?search={urllib.request.quote(word)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
        print(f"  [WARN] Fetch failed for '{word}': {e}")
        return None

    return _extract_definition(word, html)


def _extract_definition(word: str, html: str) -> dict | None:
    """Extract Zomi definition from the HTML search results page."""
    # Find the result div
    result_match = re.search(r'<div class="result">(.*?)</div>\s*<br\s*/?>', html, re.DOTALL)
    if not result_match:
        return None

    result_html = result_match.group(1)

    # Extract the Zomi definition
    definition_match = re.search(r'<p>\s*\((.*?)\)\s*(.*?)\s*</p>', result_html)
    if not definition_match:
        return None

    pos = definition_match.group(1).strip()  # Part of speech (n, v, adj, etc.)
    definition = definition_match.group(2).strip()

    # Extract language variant
    lang_match = re.search(r'<p>\s*Language:\s*(.*?)\s*</p>', result_html)
    language = lang_match.group(1).strip() if lang_match else ""

    # Clean definition — remove trailing dots
    definition = definition.rstrip(".")

    return {
        "english": word,
        "zomi": definition,
        "pos": pos,
        "language": language,
        "source": "tongdot.com",
    }


def discover_all_words(batch_size: int = 1000) -> set[str]:
    """Discover all English words in the dictionary by iterative autocomplete queries.

    Uses the autocomplete API to progressively discover words by querying
    with character prefixes (a, b, c... then aa, ab, ac... etc.)
    """
    import string

    known_words: set[str] = set()
    queue: list[str] = list(string.ascii_lowercase)  # Start with single letters

    while queue:
        prefix = queue.pop(0)
        suggestions = fetch_autocomplete(prefix)

        new_words = [w for w in suggestions if w not in known_words]
        if not new_words:
            continue

        known_words.update(new_words)
        print(f"  Prefix '{prefix}': found {len(new_words)} new words (total: {len(known_words)})")

        # If we got close to the batch size, explore deeper prefixes
        if len(new_words) >= batch_size * 0.8:
            for letter in string.ascii_lowercase:
                deeper = prefix + letter
                if deeper not in queue:
                    queue.append(deeper)

    return known_words


def crawl_all(discovered_words: set[str] | None = None, max_words: int = 0) -> list[dict]:
    """Crawl definitions for all discovered words. Saves results to JSON."""
    if discovered_words is None:
        print("Phase 1: Discovering words...")
        discovered_words = discover_all_words()
        print(f"Discovered {len(discovered_words)} unique words total")

    all_entries: list[dict] = []
    words_list = sorted(discovered_words)
    if max_words > 0:
        words_list = words_list[:max_words]

    print(f"\nPhase 2: Fetching definitions for {len(words_list)} words...")
    for i, word in enumerate(words_list):
        entry = fetch_word(word)
        if entry:
            all_entries.append(entry)

        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(words_list)} — {len(all_entries)} definitions found")

        time.sleep(CRAWL_DELAY)

    # Save results
    output_path = DATA_DATASET / "tongdot_dictionary.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for entry in all_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"\nDone! Saved {len(all_entries)} entries to {output_path}")
    return all_entries


if __name__ == "__main__":
    crawl_all()
