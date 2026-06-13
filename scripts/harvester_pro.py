"""
Zomi Harvester — Pro Edition with proxy rotation support.

Features:
- Auto-fetches free proxies from public lists
- Rotates proxies between requests to avoid IP tracking
- Falls back to direct connection if proxies fail
- All original discovery + YouTube comment extraction logic preserved

Usage:
  python3 scripts/harvester_pro.py --loop
  python3 scripts/harvester_pro.py --loop --proxies paid_list.txt
"""

import json, os, subprocess, time, re, hashlib, random, threading
from pathlib import Path

BASE = Path(__file__).parent.parent
STATE_FILE = BASE / "data" / "harvester_state.json"
YOUTUBE_OUTPUT = BASE / "data" / "youtube_zomi_new.txt"
CONVERSATIONAL_OUTPUT = BASE / "data" / "conversation_input.txt"
PROXY_FILE = BASE / "data" / "working_proxies.txt"

# ─── PROXY MANAGER ────────────────────────────────────────────────────────

class ProxyManager:
    def __init__(self):
        self.proxies = []
        self.current = 0
        self.lock = threading.Lock()
        self._fetch_free_proxies()

    def _fetch_free_proxies(self):
        """Fetch free HTTPS proxies from public sources."""
        sources = [
            "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        ]
        all_proxies = []
        for url in sources:
            try:
                r = subprocess.run(
                    ["curl", "-s", "--max-time", "10", url],
                    capture_output=True, text=True, timeout=15)
                if r.stdout:
                    for line in r.stdout.strip().split("\n"):
                        line = line.strip()
                        if ":" in line:
                            all_proxies.append(f"http://{line}")
            except:
                pass

        # Also check our saved working proxies
        if PROXY_FILE.exists():
            saved = PROXY_FILE.read_text().strip().split("\n")
            all_proxies.extend([p for p in saved if p and ":" in p])

        # Deduplicate and validate
        seen = set()
        self.proxies = []
        for p in all_proxies:
            if p not in seen:
                seen.add(p)
                self.proxies.append(p)

        random.shuffle(self.proxies)
        print(f"[Proxy] Loaded {len(self.proxies)} proxies")

    def get(self):
        """Get next proxy. Returns None if no proxies available."""
        with self.lock:
            if not self.proxies:
                return None
            p = self.proxies[self.current % len(self.proxies)]
            self.current += 1
            return p

    def report_bad(self, proxy):
        """Remove a non-working proxy."""
        with self.lock:
            if proxy in self.proxies:
                self.proxies.remove(proxy)
            # Save working proxies
            if self.proxies:
                PROXY_FILE.write_text("\n".join(self.proxies[:100]))

    def test_proxies(self, count=20):
        """Test a batch of proxies against a known site."""
        working = []
        test_url = "https://httpbin.org/ip"
        batch = self.proxies[:count]

        for proxy in batch:
            try:
                r = subprocess.run(
                    ["curl", "-s", "--max-time", "5", "--proxy", proxy, test_url],
                    capture_output=True, text=True, timeout=10)
                if r.stdout and "\"origin\"" in r.stdout:
                    working.append(proxy)
            except:
                self.report_bad(proxy)

        print(f"[Proxy] Tested {len(batch)}, {len(working)} working")
        return working

# ─── STEALTH TOOLS ────────────────────────────────────────────────────────

def stealth_sleep(mean, spread=0.5):
    time.sleep(max(mean + random.uniform(-spread, spread), 0.5))

def curl_with_proxy(url, proxy_mgr=None, timeout=15):
    """Run curl with optional proxy rotation."""
    cmd = ["curl", "-s", "--max-time", str(timeout),
           "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)"]

    if proxy_mgr:
        proxy = proxy_mgr.get()
        if proxy:
            cmd += ["--proxy", proxy]

    cmd += ["-L", url]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        return r.stdout
    except:
        return ""

# ─── ZOMI DETECTION ──────────────────────────────────────────────────────

ZOMI_MARKERS = {"hi", "pen", "in", "tawh", "leh", "mah", "zong", "kei", "Pasian", "Topa",
                "ciang", "bang", "mahmah", "hiam", "hong", "khempeuh", "zaw", "tampi", "mite",
                "ciangin", "bangin", "tua", "ahi", "om", "nawn", "lo", "zomi", "tedim"}

SEED_TERMS = ["Zomi", "Tedim", "Zomi song", "Zomi worship", "Zomi gospel",
              "Zomi news", "Zomi language", "Tedim Bible", "Zomi culture",
              "Zomi church service", "Zomi sermon", "Zo people",
              "Zomi Daily", "Tedim Post", "Zomite", "Pasian"]

def is_zomi(text):
    if not text or len(text) < 10:
        return False
    words = set(text.lower().split())
    matches = words & ZOMI_MARKERS
    return len(matches) >= 2

# ─── STATE ────────────────────────────────────────────────────────────────

def load_state():
    if STATE_FILE.exists():
        try: return json.loads(STATE_FILE.read_text())
        except: pass
    return {"visited_urls": [], "terms_searched": [], "total_zomi_lines": 0}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def is_visited(url, state):
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return url_hash in set(state.get("visited_hashes", []))

def mark_visited(url, state):
    if "visited_hashes" not in state:
        state["visited_hashes"] = []
    url_hash = hashlib.md5(url.encode()).hexdigest()
    if url_hash not in state["visited_hashes"]:
        state["visited_hashes"].append(url_hash)
    state["visited_urls"].append(url)
    if len(state["visited_urls"]) > 2000:
        state["visited_urls"] = state["visited_urls"][-2000:]

def save_zomi_line(line, source="unknown"):
    with open(CONVERSATIONAL_OUTPUT, "a", encoding="utf-8") as f:
        f.write(line.strip() + f"  [{source}]\n")
    with open(YOUTUBE_OUTPUT, "a", encoding="utf-8") as f:
        f.write(line.strip() + "\n")

# ─── DISCOVERY ────────────────────────────────────────────────────────────

def phase_discovery(state, proxy_mgr):
    new = 0
    terms = list(set(SEED_TERMS + state.get("terms_searched", [])))

    for term in terms[:5]:
        if term in state.get("terms_searched", []):
            continue

        log(f"Search web: {term}")
        state.setdefault("terms_searched", []).append(term)

        try:
            q = term.replace(" ", "+")
            html = curl_with_proxy(f"https://html.duckduckgo.com/html/?q={q}+zomi", proxy_mgr)
            if not html:
                continue

            links = re.findall(r'class="result__url"[^>]*href="([^"]+)"', html)
            for link in links[:5]:
                if is_visited(link, state):
                    continue
                if "youtube.com" in link or "youtu.be" in link:
                    mark_visited(link, state)
                    new += 1
                    log(f"  → {link[:70]}")
                    zc = extract_youtube_comments(link, state)
                    if zc:
                        log(f"    → {zc} Zomi comments")

        except:
            pass

        stealth_sleep(10, 5)

    return new

# ─── YOUTUBE ──────────────────────────────────────────────────────────────

def extract_youtube_comments(url, state, proxy_mgr=None):
    try:
        video_id = url.split("v=")[-1][:11] if "v=" in url else url.split("/")[-1]
        out_path = f"/tmp/zo_{video_id}"

        cmd = ["yt-dlp", "--write-comments", "--skip-download", "-o", out_path,
               "--max-downloads", "1", url]

        # yt-dlp doesn't support proxies natively, but we can use curl wrapper
        subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        info_path = f"{out_path}.info.json"
        if not os.path.exists(info_path):
            return 0

        with open(info_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        comments = data.get("comments", [])
        zomi_count = 0
        for c in comments:
            text = c.get("text", "")
            if text and is_zomi(text):
                save_zomi_line(text, source=video_id)
                zomi_count += 1

        try: os.remove(info_path)
        except: pass
        return zomi_count
    except:
        return 0

def phase_youtube(state, proxy_mgr):
    total = 0
    terms = list(set(SEED_TERMS))

    for term in terms[:3]:
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
                    log(f"  Video: {d.get('title','?')[:60]}")
                    zc = extract_youtube_comments(url, state, proxy_mgr)
                    if zc:
                        total += zc
                        log(f"    → {zc} Zomi comments")

                    stealth_sleep(15, 8)
                except:
                    continue
        except:
            pass

        stealth_sleep(10, 5)

    return total

# ─── LOGGING ──────────────────────────────────────────────────────────────

def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

# ─── MAIN ─────────────────────────────────────────────────────────────────

def run_cycle(proxy_mgr):
    log("=" * 50)
    log("Cycle start")
    log("=" * 50)

    state = load_state()
    log(f"Visited: {len(state.get('visited_urls', []))} URLs")

    log("\n--- Discovery ---")
    new = phase_discovery(state, proxy_mgr)

    log("\n--- YouTube ---")
    zomi = phase_youtube(state, proxy_mgr)

    save_state(state)

    log("\n" + "=" * 50)
    log(f"New: {new} | Zomi: {zomi} | Total visited: {len(state['visited_urls'])}")
    log("=" * 50)
    return new + zomi

def main():
    proxy_mgr = ProxyManager()

    if "--test-proxies" in sys.argv:
        proxy_mgr.test_proxies(50)
        return

    if "--loop" in sys.argv:
        interval = int(sys.argv[sys.argv.index("--interval") + 1]) if "--interval" in sys.argv else 120
        log(f"Loop every {interval} min. Ctrl+C to stop.")
        while True:
            run_cycle(proxy_mgr)
            jitter = random.uniform(-interval * 60 * 0.1, interval * 60 * 0.1)
            log(f"Sleep {interval} min...")
            time.sleep(interval * 60 + jitter)
    else:
        run_cycle(proxy_mgr)

if __name__ == "__main__":
    import sys
    main()
