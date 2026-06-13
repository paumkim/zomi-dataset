"""
Zomi Content Harvester — autonomous loop that discovers and collects Zomi content.
Circles: discovery → YouTube → comments → dataset → more discovery → repeats.
Tracks visited URLs, avoids duplicates, runs slowly to avoid bot detection.

Usage:
  python3 scripts/harvester.py              # Single cycle
  python3 scripts/harvester.py --loop       # Run forever (15 min between cycles)
  python3 scripts/harvester.py --loop --interval 30  # Custom interval in minutes
"""

import json, os, subprocess, time, re, hashlib
from pathlib import Path

BASE = Path(__file__).parent.parent
STATE_FILE = BASE / "data" / "harvester_state.json"
YOUTUBE_OUTPUT = BASE / "data" / "youtube_zomi_new.txt"
DISCOVERY_OUTPUT = BASE / "data" / "discovered_sources.json"
CONVERSATIONAL_OUTPUT = BASE / "data" / "conversation_input.txt"

# Zomi markers for language detection
ZOMI_MARKERS = {"hi", "pen", "in", "tawh", "leh", "mah", "zong", "kei", "Pasian", "Topa",
                "ciang", "bang", "mahmah", "hiam", "hong", "khempeuh", "zaw", "tampi", "mite",
                "ciangin", "bangin", "tua", "ahi", "om", "nawn", "lo", "zomi", "tedim"}

SEED_TERMS = [
    "Zomi", "Tedim", "Zomi song", "Zomi worship", "Zomi gospel",
    "Zomi news", "Zomi language", "Tedim Bible", "Zomi culture",
    "Zomi church service", "Zomi sermon", "Zo people",
    "Zomi Daily", "Tedim Post", "Zomite", "Pasian",
]

# Seed YouTube channels (known Zomi channels)
SEED_CHANNELS = [
    "https://youtube.com/@tedimpost",
    "https://youtube.com/@ZomiDailyNews",
    "https://youtube.com/@ZomiWorshipCollective",
    "https://youtube.com/@ZomiChristianMusic",
]


def log(msg):
    t = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{t}] {msg}")

def load_state():
    if STATE_FILE.exists():
        try: return json.loads(STATE_FILE.read_text())
        except: pass
    return {"visited_urls": [], "terms_searched": [], "total_zomi_lines": 0}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def is_zomi(text):
    if not text or len(text) < 10:
        return False
    words = set(text.lower().split())
    matches = words & ZOMI_MARKERS
    return len(matches) >= 2

def is_visited(url, state):
    # Use URL hash for efficient checking
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return url_hash in state.get("visited_hashes", set())

def mark_visited(url, state):
    if "visited_hashes" not in state:
        state["visited_hashes"] = set()
    state["visited_hashes"].add(hashlib.md5(url.encode()).hexdigest())
    state["visited_urls"].append(url)
    # Keep last 1000
    if len(state["visited_urls"]) > 1000:
        state["visited_urls"] = state["visited_urls"][-1000:]

def save_zomi_line(line, source="unknown"):
    """Save a Zomi line to the conversational dataset."""
    with open(CONVERSATIONAL_OUTPUT, "a", encoding="utf-8") as f:
        f.write(line.strip() + f"  [{source}]\n")
    # Also append to YouTube output for compatibility
    with open(YOUTUBE_OUTPUT, "a", encoding="utf-8") as f:
        f.write(line.strip() + "\n")

# ─── PHASE 1: DISCOVERY ──────────────────────────────────────────────────

def phase_discovery(state):
    """Search web for Zomi content using DuckDuckGo."""
    new_sources = 0
    terms = list(set(SEED_TERMS + state.get("terms_searched", [])))

    for term in terms[:5]:  # 5 terms per cycle
        if term in state.get("terms_searched", []):
            continue

        log(f"Search: {term}")
        state.setdefault("terms_searched", []).append(term)

        try:
            q = term.replace(" ", "+")
            r = subprocess.run(
                ["curl", "-s", f"https://html.duckduckgo.com/html/?q={q}+zomi",
                 "-H", "User-Agent: Mozilla/5.0"],
                capture_output=True, text=True, timeout=15)

            # Extract links
            links = re.findall(r'class="result__url"[^>]*href="([^"]+)"', r.stdout)
            titles = re.findall(r'class="result__title"[^>]*>.*?<a[^>]*>(.*?)</a>', r.text, re.DOTALL)

            for i, link in enumerate(links[:5]):
                if is_visited(link, state):
                    continue
                if "youtube.com" in link or "youtu.be" in link:
                    mark_visited(link, state)
                    new_sources += 1
                    log(f"  → YouTube: {link[:70]}")

                    # Extract and save video comments
                    zomi_count = extract_youtube_comments(link, state)
                    if zomi_count:
                        log(f"    → {zomi_count} Zomi comments saved")

        except Exception as e:
            log(f"  Search error: {e}")

        time.sleep(3)  # Polite delay

    return new_sources

# ─── PHASE 2: YOUTUBE EXTRACTION ─────────────────────────────────────────

def extract_youtube_comments(url, state):
    """Extract Zomi comments from a YouTube video."""
    try:
        r = subprocess.run(
            ["yt-dlp", "--no-download", "--dump-json", "--extract-comments",
             "--max-comments", "50", url],
            capture_output=True, text=True, timeout=120)

        zomi_count = 0
        for line in r.stdout.strip().split("\n"):
            if not line: continue
            try:
                d = json.loads(line)
                if "comment" in d:
                    comment = d["comment"]
                    if is_zomi(comment):
                        save_zomi_line(comment, source=url.split("v=")[-1][:11] if "v=" in url else "yt")
                        zomi_count += 1
            except:
                pass

        return zomi_count
    except:
        return 0

# ─── PHASE 3: YouTube SEARCH ─────────────────────────────────────────────

def phase_youtube_search(state):
    """Search YouTube for Zomi videos and extract comments."""
    total_zomi = 0
    terms = list(set(SEED_TERMS))

    for term in terms[:3]:  # 3 terms per cycle
        log(f"YouTube search: {term}")

        try:
            r = subprocess.run(
                ["yt-dlp", f"ytsearch10:{term} Zomi", "--dump-json", "--no-download"],
                capture_output=True, text=True, timeout=30)

            for line in r.stdout.strip().split("\n"):
                if not line: continue
                try:
                    d = json.loads(line)
                    url = f"https://youtube.com/watch?v={d['id']}"

                    if is_visited(url, state):
                        continue

                    mark_visited(url, state)
                    title = d.get("title", "?")
                    log(f"  Video: {title[:60]}")

                    # Extract comments
                    zomi_count = extract_youtube_comments(url, state)
                    if zomi_count:
                        total_zomi += zomi_count
                        log(f"    → {zomi_count} Zomi comments")

                    time.sleep(5)  # Polite delay between videos

                except:
                    continue

        except Exception as e:
            log(f"  YouTube search error: {e}")

        time.sleep(3)

    return total_zomi


def run_cycle():
    """Run one full harvest cycle."""
    log("=" * 50)
    log("Zomi Harvester — Starting cycle")
    log("=" * 50)

    state = load_state()
    log(f"Previously visited: {len(state.get('visited_urls', []))} URLs")

    # Phase 1: Discovery
    log("\n--- Phase 1: Web Discovery ---")
    new = phase_discovery(state)

    # Phase 2: YouTube Search
    log("\n--- Phase 2: YouTube Search ---")
    zomi = phase_youtube_search(state)

    # Save state
    save_state(state)

    log("\n" + "=" * 50)
    log(f"Cycle complete!")
    log(f"  New sources found: {new}")
    log(f"  Zomi comments collected: {zomi}")
    log(f"  Total visited: {len(state['visited_urls'])}")
    log("=" * 50)

    return new + zomi


def main():
    if "--loop" in sys.argv:
        interval = 15  # minutes
        if "--interval" in sys.argv:
            idx = sys.argv.index("--interval")
            interval = int(sys.argv[idx + 1])

        log(f"Harvester looping every {interval} minutes. Ctrl+C to stop.")
        while True:
            run_cycle()
            log(f"\nSleeping {interval} minutes...\n")
            time.sleep(interval * 60)
    else:
        run_cycle()

if __name__ == "__main__":
    import sys
    main()
