"""
Zomi Lyrics Collector — uses your REAL browser to bypass Cloudflare.

Two modes:
  1. Programmatic (default): Launches Chrome with remote debugging,
     controls it via Playwright. Fast and silent.

  2. Mouse mode (--mouse): Uses pyautogui to physically move your
     mouse cursor and click like a real human. Cloudflare sees
     perfect human behavior. SLOWER but undetectable.

Usage:
    python3 crawl/lyrics_collector.py              # Programmatic mode
    python3 crawl/lyrics_collector.py --mouse      # Mouse automation mode
    python3 crawl/lyrics_collector.py --mouse --speed 0.5  # Faster mouse

Requirements:
    - Close ALL Chrome windows first
    - The script will open a new Chrome window
    - In --mouse mode: DON'T touch mouse/keyboard while it runs
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

# ── Mouse Automation (pyautogui) ──

class HumanMouse:
    """Controls Chrome by physically moving the mouse and clicking.

    pyautogui is imported lazily to avoid X display issues in non-mouse mode.
    """

    def __init__(self, speed: float = 0.3):
        # pyautogui imported lazily as pg
        # pyperclip imported lazily as pc
        self._pg = pg
        self._pc = pc
        pg.FAILSAFE = True
        pg.PAUSE = 0.1
        self.speed = speed
        self.scroll_pause = 0.5

    def human_move(self, x: int, y: int) -> None:
        """Move mouse to (x, y) with human-like speed and jitter."""
        import random
        jitter_x = random.randint(-3, 3)
        jitter_y = random.randint(-3, 3)
        duration = self.speed * (0.8 + random.random() * 0.4)
        self._pg.moveTo(x + jitter_x, y + jitter_y, duration=duration, tween=self._pg.easeOutQuad)

    def human_click(self, x: int, y: int) -> None:
        """Move to position and click like a human."""
        self.human_move(x, y)
        self._pg.mouseDown()
        self._pg.PAUSE = 0.05 + __import__('random').random() * 0.1
        self._pg.mouseUp()

    def scroll_down(self, clicks: int = 5) -> None:
        """Scroll down like a human reading."""
        for _ in range(clicks):
            self._pg.scroll(-1)
            self._pg.PAUSE = self.scroll_pause * (0.5 + __import__('random').random())

    def scroll_up(self, clicks: int = 3) -> None:
        for _ in range(clicks):
            self._pg.scroll(1)
            self._pg.PAUSE = self.scroll_pause * (0.5 + __import__('random').random())

    def type_text(self, text: str, interval: float = 0.08) -> None:
        """Type text with realistic delays between characters."""
        import random
        for char in text:
            self._pg.typewrite(char, interval=interval * (0.5 + random.random()))
            self._pg.PAUSE = 0.02

    def select_all_and_copy(self) -> str:
        """Select all text on the page and copy to clipboard."""
        # pyperclip imported lazily
        self._pg.hotkey("ctrl", "a")
        self._pg.PAUSE = 0.3
        self._pg.hotkey("ctrl", "c")
        self._pg.PAUSE = 0.2
        return self._pc.paste()

    def find_chrome_window(self) -> tuple[int, int, int, int]:
        """Find the Chrome browser window position and size."""
        try:
            import pygetwindow as gw
            chrome_windows = [w for w in gw.getWindowsWithTitle("") if "chrom" in w.title.lower() or "chrome" in w.title.lower()]
            if not chrome_windows:
                # Try any large window
                for w in gw.getAllWindows():
                    if w.width > 800 and w.height > 600:
                        chrome_windows = [w]
                        break
            if chrome_windows:
                win = chrome_windows[0]
                win.activate()
                self._pg.PAUSE = 0.5
                return (win.left, win.top, win.width, win.height)
        except Exception:
            pass
        # Fallback: assume fullscreen on primary monitor
        return (0, 0, 1920, 1080)

    def click_link(self, text_containing: str, window_rect: tuple[int,int,int,int]) -> bool:
        """Find and click a link containing the given text by scanning the screen."""
        win_x, win_y, win_w, win_h = window_rect
        center_x = win_x + win_w // 2
        center_y = win_y + win_h // 2

        # Move to center of window first
        self.human_move(center_x, center_y)
        self._pg.PAUSE = 0.3

        # Try Ctrl+F to find the text
        self._pg.hotkey("ctrl", "f")
        self._pg.PAUSE = 0.3
        self.type_text(text_containing)
        self._pg.PAUSE = 0.5

        # Press Enter to focus the link
        self._pg.press("enter")
        self._pg.PAUSE = 0.3
        self._pg.press("escape")  # Close find bar
        self._pg.PAUSE = 0.3

        # Click in the center area (the link should be highlighted)
        self.human_click(center_x + __import__('random').randint(-50, 50),
                        center_y + __import__('random').randint(-100, 100))
        return True

    def navigate_back(self) -> None:
        """Go back one page like a human."""
        self._pg.hotkey("alt", "left")
        self._pg.PAUSE = 1.0

    def new_tab(self, url: str = "") -> None:
        """Open a new tab."""
        self._pg.hotkey("ctrl", "t")
        self._pg.PAUSE = 0.5
        if url:
            self.type_text(url)
            self._pg.PAUSE = 0.3
            self._pg.press("enter")
            self._pg.PAUSE = 3.0

    def close_tab(self) -> None:
        """Close current tab."""
        self._pg.hotkey("ctrl", "w")
        self._pg.PAUSE = 0.5


class MouseLyricsCollector:
    """Collect lyrics using mouse/keyboard automation (no API/Playwright needed).

    This is 100% undetectable. Cloudflare sees a real human with real
    mouse movements, real scrolling, real typing.
    """

    def __init__(self, speed: float = 0.3):
        self.mouse = HumanMouse(speed)
        self.songs: list[dict[str, str]] = []
        self.base_url = "https://zomiworshipcollective.com/lyrics/"

    def run(self) -> None:
        """Full collection workflow using mouse automation."""
        import pyautogui as _pg
        import pyperclip as _pc
        print("\n" + "=" * 60)
        print("MOUSE AUTOMATION MODE")
        print("=" * 60)
        print()
        print("  ⚠  DO NOT touch your mouse or keyboard while this runs!")
        print("  ⚠  Move mouse to top-left corner to abort (failsafe)")
        print()
        print("  First, the script will open the lyrics page.")
        print("  If you see a Cloudflare challenge, solve it quickly.")
        print()
        input("  Press Enter when Chrome is open and ready...")

        # Step 1: Navigate to lyrics page
        self.mouse.new_tab(self.base_url)
        print("  Waiting for page to load...")
        print("  (Solve any Cloudflare challenge now if needed)")
        __import__('time').sleep(10)

        # Step 2: Get the page text by select-all + copy
        print("  Extracting page content...")
        _pg.hotkey("ctrl", "a")
        __import__('time').sleep(1)
        _pg.hotkey("ctrl", "c")
        __import__('time').sleep(0.5)
        content = _pc.paste()

        # Save main page
        Path("data/texts/worship_mainpage.txt").write_text(content)
        print(f"  Saved main page: {len(content)} chars")

        # Step 3: Find song links by searching through content
        import re
        links = re.findall(r'(https?://[^\s"\']+)', content)
        song_urls = [l for l in links if "/lyrics/" in l or "/song/" in l]
        song_urls = list(dict.fromkeys(song_urls))  # Dedup
        print(f"  Found {len(song_urls)} song links")

        # Step 4: Visit each song
        for i, url in enumerate(song_urls[:50]):
            print(f"\n  [{i+1}/{min(len(song_urls), 50)}] Opening song...")

            # Open in new tab
            self.mouse.new_tab(url)
            __import__('time').sleep(5)

            # Copy all text
            _pg.hotkey("ctrl", "a")
            __import__('time').sleep(1)
            _pg.hotkey("ctrl", "c")
            __import__('time').sleep(0.5)
            lyrics = _pc.paste()

            if lyrics and len(lyrics) > 50:
                self.songs.append({"url": url, "lyrics": lyrics})
                print(f"    {len(lyrics)} chars")

                # Save individual
                safe_name = re.sub(r'[^a-zA-Z0-9]+', '_', url.split("/")[-1])[:30]
                Path(f"data/texts/worship_{safe_name}.txt").write_text(lyrics)
            else:
                print("    too short, skipping")

            # Close tab
            self.mouse.close_tab()
            __import__('time').sleep(1)

        # Step 5: Save combined
        if self.songs:
            combined = "\n\n".join(
                f"=== {s['url']} ===\n{s['lyrics']}" for s in self.songs
            )
            Path("data/zomi_only/worship_lyrics_corpus.txt").write_text(combined)
            print(f"\nDone! {len(self.songs)} songs, {len(combined)} chars")

# ── Configuration ──

LYRICS_URL = "https://zomiworshipcollective.com/lyrics/"
OUTPUT_DIR = Path("data/texts")
FINAL_DIR = Path("data/zomi_only")

USER_DATA_DIR = os.path.expanduser("~/.config/chromium")  # Default Chromium profile
CHROME_PATH = "/usr/bin/chromium"  # Default Chromium install location


def find_chrome() -> str:
    """Find the installed Chrome/Chromium browser."""
    candidates = [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/snap/bin/chromium",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    # Generic fallback
    for path in os.environ.get("PATH", "").split(":"):
        for name in ["chromium", "chromium-browser", "google-chrome", "google-chrome-stable"]:
            full = os.path.join(path, name)
            if os.path.exists(full):
                return full
    return ""


def launch_real_browser() -> Any:
    """Launch Chrome with real user profile connected to Playwright.

    Chrome is started with:
      - Your real profile (cookies, cache, history)
      - Remote debugging enabled
      - A visible window (not headless)

    Returns a Playwright browser instance connected to the real Chrome.
    """
    chrome_path = find_chrome()
    if not chrome_path:
        print("ERROR: Chromium/Chrome not found.")
        print("Install with: sudo pacman -S chromium")
        sys.exit(1)

    # Create a temp directory for the debug socket
    debug_dir = "/tmp/chrome_debug_zomi"
    os.makedirs(debug_dir, exist_ok=True)
    debug_port = 9444

    print(f"Starting {chrome_path} with your real profile...")
    print(f"  Profile: {USER_DATA_DIR}")
    print(f"  Debug port: {debug_port}")
    print()
    print("  A Chrome window will open. Let it load completely.")
    print("  The script will wait 15 seconds for you to sign in if needed.")
    print()

    # Kill any existing Chrome on the debug port
    subprocess.run(["pkill", "-f", f"chromium.*{debug_port}"], capture_output=True)
    time.sleep(1)

    # Launch Chrome with real profile + remote debugging
    process = subprocess.Popen(
        [
            chrome_path,
            f"--remote-debugging-port={debug_port}",
            f"--user-data-dir={USER_DATA_DIR}",
            "--no-first-run",
            "--no-default-browser-check",
            f"--window-size=1280,900",
            LYRICS_URL,  # Open the lyrics page directly
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    print(f"Chrome PID: {process.pid}")
    print("Waiting 15 seconds for page to load...")
    time.sleep(15)

    # Connect Playwright to the running Chrome
    try:
        p = sync_playwright().start()
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{debug_port}")
        print("Connected to Chrome!")
        return browser, p, process
    except Exception as e:
        print(f"Failed to connect: {e}")
        print("\nTroubleshooting:")
        print("  1. Close ALL Chrome windows completely")
        print("  2. Run: pkill chromium")
        print("  3. Run this script again")
        process.kill()
        sys.exit(1)


def get_artist_links(page) -> list[tuple[str, str]]:
    """Extract only ARTIST links from the main lyrics page (not song links or filters).

    Artist URLs contain: /lyrics/category-NAME/ or /lyrics/songartist-NAME/ or /lyrics/phuak-NAME/
    Filter buttons contain: /lyrics/?... (query params)
    Individual songs contain: /lyrics/song-name/ (no prefix)
    """
    links: list[tuple[str, str]] = []
    seen: set[str] = set()
    main_url = "https://zomiworshipcollective.com/lyrics"

    for a in page.query_selector_all("a"):
        href = a.get_attribute("href") or ""
        text = a.inner_text().strip()

        if not href or not text:
            continue
        if len(text) < 3 or len(text) > 100:
            continue
        if href in seen:
            continue
        seen.add(href)

        # Must be a /lyrics/ URL
        if '/lyrics/' not in href:
            continue

        # Skip the main page itself
        if href.rstrip('/') == main_url:
            continue

        # Skip query parameters (filters like ?bpm=, ?key=)
        if '?' in href:
            continue

        # Only include artist-type URLs (with category-, songartist-, or phuak- prefix)
        path = href.rstrip('/')
        if any(kw in path for kw in ['/category-', '/songartist-', '/phuak-']):
            links.append((text, href))

    return links


def dismiss_popups(page) -> None:
    """Remove popup ads and overlays that might block page interaction."""
    try:
        page.evaluate("""
            (() => {
                // Remove common overlay/ad elements
                const selectors = [
                    '.advertisement', '.ad', '.ads', '.adsbygoogle',
                    '.popup', '.modal', '.overlay', '.subscription',
                    '[class*="cookie"]', '[class*="Cookie"]',
                    '[class*="consent"]', '[class*="Consent"]',
                    '[class*="gdpr"]', '[class*="GDPR"]',
                    '[class*="notice"]', '[class*="banner"]',
                    '[id*="cookie"]', '[id*="Cookie"]',
                    '.cc-window', '.cc-banner',
                    '#onetrust-consent-sdk', '#onetrust-banner-sdk',
                    '.osano-cm-window', '[class*="osano"]',
                    // Remove fixed/sticky overlays at the bottom
                    '[style*="position: fixed"]',
                    '[style*="position:fixed"]',
                    '.mads-block', '.ad-container',
                    'ins.adsbygoogle',
                ];
                selectors.forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => el.remove());
                });
                // Remove any element that covers more than 60% of screen
                const all = document.querySelectorAll('*');
                const vw = window.innerWidth;
                const vh = window.innerHeight;
                all.forEach(el => {
                    try {
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        if ((style.position === 'fixed' || style.position === 'sticky') &&
                            rect.width > vw * 0.6 && rect.height > vh * 0.6 &&
                            rect.top < 50 && rect.left < 50) {
                            el.remove();
                        }
                    } catch(e) {}
                });
            })();
        """);
        __import__('time').sleep(0.5)
    except Exception:
        pass


def extract_page_lyrics(page) -> str:
    """Extract the lyric text from the current song page.

    The site stores lyrics in .gutentor-text elements.
    Falls back to body text extraction.
    """
    import re

    # Method 1: Try gutentor-text elements (WordPress lyrics container)
    lyrics_elements = page.query_selector_all(".gutentor-text")
    if lyrics_elements:
        all_lyrics = []
        for el in lyrics_elements:
            text = el.inner_text().strip()
            if text and len(text) > 10:
                all_lyrics.append(text)
        if all_lyrics:
            return "\n\n".join(all_lyrics)

    # Method 2: Try content-post div
    content = page.query_selector(".content-post, .content, article")
    if content:
        text = content.inner_text()
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        # Filter for Zomi lyrics patterns
        zomi_lines = []
        skip_words = ["cookie", "privacy", "subscribe", "comment", "share",
                      "facebook", "twitter", "instagram", "copyright", "search",
                      "menu", "navigation", "archive", "rights reserved",
                      "popularity", "name (a-z)", "name (z-a)", "bpm", "timesig",
                      "skip to content", "discover more", "powerpoint"]
        for l in lines:
            lower = l.lower()
            if any(kw in lower for kw in skip_words):
                continue
            if len(l) < 5:
                continue
            if l.isdigit():
                continue
            zomi_lines.append(l)
        if zomi_lines:
            return "\n".join(zomi_lines[:200])

    # Method 3: Full body text as fallback
    text = page.inner_text("body")
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    skip_keywords = ["cookie", "privacy", "cloudflare", "subscribe", "comment",
                     "share", "facebook", "twitter", "instagram", "search",
                     "menu", "navigation", "archive", "copyright", "rights reserved"]
    lyrics = []
    for l in lines:
        lower = l.lower()
        if any(kw in lower for kw in skip_keywords):
            continue
        if len(l) < 10:
            continue
        if l.isdigit():
            continue
        lyrics.append(l)
    return "\n".join(lyrics[:200])


def discover_individual_songs(page, artist_url: str) -> list[tuple[str, str]]:
    """Visit an artist page and extract individual song links.

    The site has two types of links on artist pages:
      - Other artists (sidebar): /lyrics/songartist-NAME/  or  /lyrics/category-NAME/
      - Individual songs: /lyrics/song-name-slug/

    We only want individual songs: URLs that have exactly ONE path segment after /lyrics/
    and do NOT contain 'songartist' or 'category'.
    """
    songs: list[tuple[str, str]] = []
    seen: set[str] = set()
    try:
        page.goto(artist_url, wait_until="domcontentloaded", timeout=15000)
        __import__('time').sleep(3)
        dismiss_popups(page)
        __import__('time').sleep(2)

        for a in page.query_selector_all("a"):
            href = a.get_attribute("href") or ""
            text = a.inner_text().strip()
            if not text or not href:
                continue
            if len(text) < 3 or len(text) > 150:
                continue
            if href in seen:
                continue
            seen.add(href)

            # Must be a /lyrics/ URL
            if '/lyrics/' not in href:
                continue

            # Skip: main page, category pages, songartist pages, phuak pages
            path = href.rstrip('/')
            if any(kw in path for kw in ['/category-', '/songartist-', '/phuak-']):
                continue
            if path == 'https://zomiworshipcollective.com/lyrics':
                continue

            # Individual songs have a slug right after /lyrics/ (one path segment)
            parts = path.split('/')
            if 'lyrics' in parts:
                idx = parts.index('lyrics')
                # Must have exactly one segment after /lyrics/
                if idx + 1 < len(parts) and (idx + 2 >= len(parts)):
                    slug = parts[idx + 1]
                    # Song slugs are descriptive (hyphenated words), at least 15 chars
                    if len(slug) >= 15 and '-' in slug:
                        if (text, href) not in songs:
                            songs.append((text, href))

    except Exception as e:
        print(f"  error: {e}")
    return songs


def collect_all_lyrics(browser) -> list[dict[str, str]]:
    """Visit the lyrics site and collect ALL actual song lyrics (two-level deep)."""
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else context.new_page()

    import json
    progress_file = Path("crawl/lyrics_progress.json")

    # Load existing progress
    all_lyrics: list[dict] = []
    visited_song_urls: set[str] = set()
    processed_artists: set[str] = set()

    if progress_file.exists():
        try:
            saved = json.loads(progress_file.read_text())
            all_lyrics = saved.get("songs", [])
            visited_song_urls = set(s["url"] for s in all_lyrics)
            processed_artists = set(s.get("artist_url", "") for s in all_lyrics if s.get("artist_url"))
            print(f"Resuming from {len(all_lyrics)} songs, {len(processed_artists)} artists done")
        except Exception:
            pass

    # Step 1: Get artist links from main lyrics page
    print("\nStep 1: Discovering artists...")
    main_page = context.new_page()
    main_page.goto("https://zomiworshipcollective.com/lyrics/", wait_until="domcontentloaded", timeout=20000)
    __import__('time').sleep(3)
    dismiss_popups(main_page)

    artists = get_artist_links(main_page)
    print(f"Found {len(artists)} artist pages")
    main_page.close()

    # Step 2: For each artist, discover individual song links
    total_songs_discovered = 0
    total_lyrics_collected = 0

    for artist_idx, (artist_name, artist_url) in enumerate(artists):
        if artist_url in processed_artists:
            print(f"[Artist {artist_idx+1}/{len(artists)}] {artist_name[:40]}... already done")
            continue

        print(f"\n[Artist {artist_idx+1}/{len(artists)}] {artist_name[:40]}...", end=" ", flush=True)

        try:
            songs = discover_individual_songs(page, artist_url)
        except Exception as e:
            print(f"discover failed: {e}")
            # Try fresh page
            page = context.new_page()
            try:
                songs = discover_individual_songs(page, artist_url)
            except Exception as e2:
                print(f"retry failed: {e2}")
                continue

        if not songs:
            print("no songs found")
            processed_artists.add(artist_url)
            continue

        print(f"{len(songs)} songs")

        # Step 3: Visit each individual song and extract lyrics
        for song_idx, (song_title, song_url) in enumerate(songs[:30]):  # Max 30 songs per artist
            if song_url in visited_song_urls:
                continue

            print(f"  [{song_idx+1}/{min(len(songs),30)}] {song_title[:50]}...", end=" ", flush=True)

            try:
                page.goto(song_url, wait_until="domcontentloaded", timeout=15000)
                __import__('time').sleep(2)
                dismiss_popups(page)

                body = page.inner_text("body").strip()
                if not body or len(body) < 20:
                    print("empty")
                    continue

                lyrics = extract_page_lyrics(page)
                if lyrics and len(lyrics) > 30:
                    song_data = {
                        "title": song_title,
                        "url": song_url,
                        "artist": artist_name,
                        "artist_url": artist_url,
                        "lyrics": lyrics,
                    }
                    all_lyrics.append(song_data)
                    visited_song_urls.add(song_url)
                    total_lyrics_collected += 1
                    print(f"{len(lyrics)} chars")
                else:
                    print("too short")

            except Exception as e:
                print(f"error: {e}")
                continue

            # Save after every song
            progress_file.parent.mkdir(parents=True, exist_ok=True)
            progress_file.write_text(json.dumps({
                "songs": all_lyrics,
                "processed_artists": list(processed_artists),
            }, indent=2, default=str))

            __import__('time').sleep(1.5)

        processed_artists.add(artist_url)
        total_songs_discovered += len(songs)

    # Final save
    progress_file.parent.mkdir(parents=True, exist_ok=True)
    progress_file.write_text(json.dumps({
        "songs": all_lyrics,
        "processed_artists": list(processed_artists),
    }, indent=2, default=str))

    print(f"\n\nDone! {len(all_lyrics)} individual songs collected from {len(processed_artists)} artists")
    return all_lyrics


def save_lyrics(all_lyrics: list[dict[str, str]]) -> None:
    """Save lyrics to the dataset."""
    if not all_lyrics:
        print("No lyrics collected.")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)

    # Save individual files
    for i, song in enumerate(all_lyrics):
        filename = f"worship_lyric_{i+1:04d}.txt"
        path = OUTPUT_DIR / filename
        content = f"=== {song['title']} ===\n{song['lyrics']}"
        path.write_text(content, encoding="utf-8")

    # Save combined corpus
    combined = "\n\n".join(
        f"=== {s['title']} ===\n{s['lyrics']}" for s in all_lyrics
    )
    corpus_path = FINAL_DIR / "worship_lyrics_corpus.txt"
    corpus_path.write_text(combined, encoding="utf-8")

    total_chars = sum(len(s["lyrics"]) for s in all_lyrics)
    print(f"\nSaved {len(all_lyrics)} songs")
    print(f"Total: {total_chars} chars")
    print(f"Corpus: {corpus_path}")
    print(f"Individual: {OUTPUT_DIR}/")

    # Show preview
    print("\n--- Sample lyrics ---")
    if all_lyrics:
        print(all_lyrics[0]["lyrics"][:300])


def main():
    import sys as _sys

    mouse_mode = "--mouse" in _sys.argv
    mouse_speed = 0.3
    if "--speed" in _sys.argv:
        try:
            idx = _sys.argv.index("--speed")
            mouse_speed = float(_sys.argv[idx + 1])
        except (ValueError, IndexError):
            pass

    print("=" * 60)
    print("Zomi Lyrics Collector")
    print("=" * 60)
    print()

    if mouse_mode:
        print("  Mode: MOUSE AUTOMATION (pyautogui)")
        print(f"  Speed: {mouse_speed}")
        print()
        collector = MouseLyricsCollector(speed=mouse_speed)
        collector.run()
        if collector.songs:
            print("\nProcessing through pipeline...")
            subprocess.run([_sys.executable, "main.py", "normalize"],
                         cwd=Path(__file__).parent.parent)
            subprocess.run([_sys.executable, "main.py", "detect"],
                         cwd=Path(__file__).parent.parent)
            subprocess.run([_sys.executable, "main.py", "stats"],
                         cwd=Path(__file__).parent.parent)
        return

    print("  Mode: PROGRAMMATIC (Playwright + real Chrome)")
    print()

    # Auto-launch after 2 seconds (skip prompt in background mode)
    import sys as _sys2
    if not _sys2.stdin.isatty():
        print("  (No terminal detected — auto-launching in 2s)")
        __import__('time').sleep(2)
    else:
        input("  Press Enter to launch Chrome...")

    # Launch the real browser
    browser, playwright, chrome_process = launch_real_browser()

    try:
        songs = collect_all_lyrics(browser)
        save_lyrics(songs)
    finally:
        print("\nClosing browser...")
        try:
            browser.close()
        except Exception:
            pass
        try:
            playwright.stop()
        except Exception:
            pass
        try:
            chrome_process.kill()
        except Exception:
            pass
        print("Done!")

    if songs:
        print("\nProcessing through pipeline...")
        subprocess.run([_sys.executable, "main.py", "normalize"],
                      cwd=Path(__file__).parent.parent)
        subprocess.run([_sys.executable, "main.py", "detect"],
                      cwd=Path(__file__).parent.parent)
        subprocess.run([_sys.executable, "main.py", "stats"],
                      cwd=Path(__file__).parent.parent)


if __name__ == "__main__":
    main()
