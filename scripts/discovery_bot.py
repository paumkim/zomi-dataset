#!/usr/bin/env python3
"""
Zomi Data Discovery Bot — finds Zomi content from public sources.
Searches YouTube, web, and news for new Zomi text to add to the dataset.

Usage: python3 scripts/discovery_bot.py
"""

import re, json, os, time, urllib.request, urllib.parse
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DISCOVERY_FILE = BASE_DIR / "data" / "discovered_sources.json"
LOG_FILE = BASE_DIR / "data" / "discovery_log.txt"

# Seed terms — the bot generates more from these
SEED_TERMS = [
    "Zomi", "Tedim", "Zo people", "Zomi language",
    "Zomi song", "Tedim Bible", "Zomi news",
    "Zomi church", "Zomi culture", "Pasian",
    "Zomi Daily", "Tedim Post", "Zomi worship",
]

# Known sources
KNOWN_SOURCES = [
    "youtube.com/@tedimpost",
    "youtube.com/@ZomiDailyNews",
    "tedimpost.com",
    "zomidaily.com",
    "zomiworshipcollective.com",
]

def log(msg):
    t = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{t}] {msg}\n")
    print(f"[{t}] {msg}")

def search_youtube(query, max_results=5):
    """Search YouTube for Zomi content. Uses API key if available, falls back to web search."""
    results = []

    # Try YouTube Data API first (requires free API key from Google Cloud Console)
    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if api_key:
        try:
            q = urllib.parse.quote(f"{query} Zomi")
            url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={q}&maxResults={max_results}&type=video&key={api_key}"
            req = urllib.request.Request(url)
            resp = json.loads(urllib.request.urlopen(req, timeout=10).read())

            for item in resp.get("items", []):
                vid = item["id"]["videoId"]
                title = item["snippet"]["title"]
                results.append({
                    "title": title,
                    "url": f"https://youtube.com/watch?v={vid}",
                    "source": "youtube",
                    "query": query,
                })
            return results
        except Exception as e:
            log(f"YouTube API error: {e} — falling back to web search")

    # Fallback: search via DuckDuckGo (no API key needed)
    try:
        q = urllib.parse.quote(f"site:youtube.com {query} Zomi")
        url = f"https://html.duckduckgo.com/html/?q={q}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="ignore")

        snippets = re.findall(r'class="result__snippet">(.*?)</a>', html, re.DOTALL)[:max_results]
        links = re.findall(r'class="result__url"[^>]*href="([^"]+)"', html)[:max_results]

        for snippet, link in zip(snippets, links):
            clean = re.sub(r'<[^>]+>', '', snippet).strip()
            results.append({
                "title": clean[:100],
                "url": link,
                "source": "youtube (via web)",
                "query": query,
            })
    except Exception as e:
        log(f"YouTube search fallback error: {e}")
    return results

def search_web(query, max_results=5):
    """Search public web for Zomi content via DuckDuckGo."""
    results = []
    try:
        q = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={q}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="ignore")

        snippets = re.findall(r'class="result__snippet">(.*?)</a>', html, re.DOTALL)
        links = re.findall(r'class="result__url"[^>]*href="([^"]+)"', html)

        for i, (snippet, link) in enumerate(zip(snippets[:max_results], links[:max_results])):
            clean = re.sub(r'<[^>]+>', '', snippet).strip()
            results.append({
                "snippet": clean[:200],
                "url": link,
                "source": "web",
                "query": query,
            })
    except Exception as e:
        log(f"Web search error for '{query}': {e}")
    return results

def load_discovered():
    if DISCOVERY_FILE.exists():
        return json.loads(DISCOVERY_FILE.read_text())
    return {"terms": [], "sources": [], "discovered": []}

def save_discovered(data):
    DISCOVERY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

def run():
    log("=" * 50)
    log("Zomi Discovery Bot — Starting")
    log("=" * 50)

    discovered = load_discovered()
    all_terms = list(set(SEED_TERMS + discovered.get("terms", [])))
    log(f"Seed terms: {len(all_terms)}")

    new_sources = []

    # Search each term
    for term in all_terms[:10]:  # Limit to 10 terms per run
        log(f"Searching: {term}")

        # YouTube
        for result in search_youtube(term):
            url = result["url"]
            if url not in [s["url"] for s in discovered["discovered"]]:
                new_sources.append(result)
                log(f"  YouTube: {result['title'][:60]}")

        # Web
        for result in search_web(term):
            url = result["url"]
            if url not in [s["url"] for s in discovered["discovered"]]:
                new_sources.append(result)
                log(f"  Web: {result['snippet'][:60]}...")

        time.sleep(1)  # Be polite

    # Add new sources
    discovered["discovered"] = (discovered["discovered"] + new_sources)[-500:]
    save_discovered(discovered)

    log(f"\nDone. New sources found: {len(new_sources)}")
    log(f"Total tracked: {len(discovered['discovered'])}")

if __name__ == "__main__":
    run()
