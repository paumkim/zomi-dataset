#!/usr/bin/env python3
"""
Zomi Deep Discovery Bot — finds archived Zomi content from the deep web.

Searches:
- Wayback Machine (archived Zomi sites)
- Public web via DuckDuckGo
- Detects Zomi language vs English
- Collects translation pairs (Zomi-English)

Usage: python3 scripts/deep_discovery.py
"""

import re, json, os, time, urllib.request, urllib.parse, hashlib
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DISCOVERY_FILE = BASE_DIR / "data" / "deep_discovered.json"
LOG_FILE = BASE_DIR / "data" / "deep_discovery_log.txt"
TRANSLATION_FILE = BASE_DIR / "data" / "translation_pairs.jsonl"

# Zomi language markers — words that strongly indicate Zomi
ZOMI_MARKERS = {
    "hi", "pen", "tawh", "ahi", "ci", "mite", "khempeuh",
    "ciangin", "bangin", "mahmah", "hiam", "hong", "om",
    "nawn", "ke'", "ke'n", "kei", "kong", "Pasian", "Topa",
    "Laisiangtho", "Zeisu", "Khazih", "Gam", "Minam",
    "kammal", "thu", "pau", "gam", "sinna", "kicing",
}

# Zomi particles — very strong indicators
ZOMI_PARTICLES = {"in", "pen", "tawh", "leh", "mah", "zong", "ciang", "bang"}

ZOMI_DOMAINS = [
    "zomi", "tedim", "zolai", "zo",
    "khristian", "laisiangtho",
]

def log(msg):
    t = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{t}] {msg}\n")
    print(f"[{t}] {msg}")

def is_zomi(text):
    """Detect if text is likely Zomi based on marker words."""
    if not text or len(text) < 20:
        return False
    words = set(text.lower().split())
    matches = words & ZOMI_MARKERS
    particle_matches = words & ZOMI_PARTICLES
    score = len(matches) * 2 + len(particle_matches)
    return score >= 3

def extract_translation_pairs(text):
    """Find Zomi-English parallel text (e.g. Zomi line followed by English translation)."""
    pairs = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    i = 0
    while i < len(lines) - 1:
        if is_zomi(lines[i]) and not is_zomi(lines[i+1]):
            # Check if next line is English (contains common English words)
            eng_words = {"the", "is", "are", "was", "were", "have", "has", "been", "will", "would", "could", "should", "this", "that", "these", "those"}
            next_words = set(lines[i+1].lower().split())
            if next_words & eng_words:
                pairs.append({"zomi": lines[i][:500], "english": lines[i+1][:500]})
                i += 2
                continue
        i += 1
    return pairs

# ─── Wayback Machine Discovery ──────────────────────────────────────────

def search_wayback(domain_filter=None, max_pages=20):
    """Search Wayback Machine CDX API for archived Zomi content."""
    results = []

    # Zomi-related domains to check
    domains = [
        "zomidaily.com", "tedimpost.com", "zomiworshipcollective.com",
        "zomibethelchurch.com", "zomilibrary.blogspot.com",
        "zomidictionary.com", "tongdot.com", "zomilaisiangtho.com",
        "zomionlinelyrics.blogspot.com",
    ]

    for domain in domains:
        try:
            url = f"https://web.archive.org/cdx/search/cdx?url={domain}&output=json&limit={max_pages}&fl=timestamp,original,mimetype,statuscode"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=15).read().decode("utf-8")
            rows = json.loads(resp)

            for row in rows[1:]:  # Skip header
                ts, orig, mime, status = row[:4]
                if status == "200" and mime.startswith("text/"):
                    results.append({
                        "url": orig,
                        "archive_url": f"https://web.archive.org/web/{ts}/{orig}",
                        "timestamp": ts,
                        "domain": domain,
                    })
        except Exception as e:
            log(f"Wayback error for {domain}: {e}")
        time.sleep(1)

    log(f"Wayback: found {len(results)} archived pages")
    return results

def fetch_archive_content(archive_url):
    """Fetch text content from Wayback Machine archive."""
    try:
        req = urllib.request.Request(archive_url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", errors="ignore")
        # Strip HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:5000]
    except:
        return ""

# ─── Web Discovery ───────────────────────────────────────────────────────

def search_web_zomi(query, max_results=10):
    """Search for Zomi content on the public web."""
    results = []
    try:
        q = urllib.parse.quote(f"{query}")
        url = f"https://html.duckduckgo.com/html/?q={q}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="ignore")

        snippets = re.findall(r'class="result__snippet">(.*?)</a>', html, re.DOTALL)
        links = re.findall(r'class="result__url"[^>]*href="([^"]+)"', html)

        for snippet, link in zip(snippets[:max_results], links[:max_results]):
            clean = re.sub(r'<[^>]+>', '', snippet).strip()
            results.append({"snippet": clean, "url": link})
    except Exception as e:
        log(f"Web search error: {e}")
    return results

# ─── Main ────────────────────────────────────────────────────────────────

def load_state():
    if DISCOVERY_FILE.exists():
        return json.loads(DISCOVERY_FILE.read_text())
    return {"archives_checked": [], "zomi_pages": [], "total_found": 0}

def save_state(state):
    DISCOVERY_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))

def save_translation(pair):
    with open(TRANSLATION_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(pair, ensure_ascii=False) + "\n")

def run():
    log("=" * 60)
    log("Zomi Deep Discovery Bot — Finding Hidden Gold")
    log("=" * 60)

    state = load_state()
    new_zomi = 0
    new_pairs = 0

    # Phase 1: Wayback Machine
    log("\n--- Phase 1: Wayback Machine ---")
    archives = search_wayback()
    for page in archives:
        if page["url"] in state["archives_checked"]:
            continue
        state["archives_checked"].append(page["url"])
        content = fetch_archive_content(page["archive_url"])
        if not content:
            continue
        if is_zomi(content):
            state["zomi_pages"].append({
                "url": page["url"],
                "archive": page["archive_url"],
                "preview": content[:200],
            })
            new_zomi += 1
            log(f"  ✓ Zomi content: {page['url'][:60]}")

            # Extract translation pairs
            pairs = extract_translation_pairs(content)
            for p in pairs:
                save_translation(p)
                new_pairs += 1

        state["total_found"] = len(state["zomi_pages"])
        save_state(state)

    # Phase 2: Fresh web search with Zomi-specific queries
    log("\n--- Phase 2: Web Search ---")
    queries = [
        "zomi tedim language", "zomi bible", "zomi song lyrics",
        "site:blogspot.com zomi", "zomi worship", "zomi sermon",
        "zomi culture", "tedim zomi news", "zomi dictionary",
        "zomi poem", "zomi story", "zomi tradition",
    ]

    for query in queries:
        log(f"Searching: {query}")
        for result in search_web_zomi(query):
            snippet = result["snippet"]
            if is_zomi(snippet) and result["url"] not in [p["url"] for p in state["zomi_pages"]]:
                state["zomi_pages"].append({
                    "url": result["url"],
                    "archive": "",
                    "preview": snippet[:200],
                })
                new_zomi += 1
                log(f"  ✓ Zomi: {result['url'][:60]}")
                state["total_found"] = len(state["zomi_pages"])
                save_state(state)
        time.sleep(1.5)

    # Summary
    log("\n" + "=" * 60)
    log(f"Summary:")
    log(f"  New Zomi pages:     {new_zomi}")
    log(f"  New translation pairs: {new_pairs}")
    log(f"  Total Zomi tracked: {state['total_found']}")
    log(f"  Archives checked:   {len(state['archives_checked'])}")
    log("=" * 60)

if __name__ == "__main__":
    run()
