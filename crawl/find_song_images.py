"""
Download all song images from the main lyrics listing page in ONE go.
Opens the main page once, extracts all image URLs, then downloads them.
"""
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from crawl.lyrics_collector import launch_real_browser, LYRICS_URL

output_dir = Path.home() / "zomi_dataset" / "data" / "song_images"
output_dir.mkdir(parents=True, exist_ok=True)

# Load songs from progress
progress_path = Path(__file__).parent.parent / "crawl" / "lyrics_progress.json"
songs = json.loads(progress_path.read_text()).get("songs", [])
print(f"Total songs: {len(songs)}")

# Launch browser ONCE
browser, playwright, chrome_process = launch_real_browser()
page = browser.new_page()

print("\nNavigating to main lyrics page...")
page.goto("https://zomiworshipcollective.com/lyrics/", timeout=30000, wait_until="networkidle")
print("Page loaded. Give it a moment...")
time.sleep(3)

# Get all image URLs from the main page
images = page.eval_on_selector_all("img", 
    "elements => elements.map(e => ({src: e.src, alt: e.alt, width: e.naturalWidth, height: e.naturalHeight, cls: e.className}))")

print(f"\nFound {len(images)} images on the page")
print("\n=== Image URLs ===")
for img in images:
    src = img.get("src", "")
    alt = img.get("alt", "")
    w = img.get("width", 0)
    h = img.get("height", 0)
    cls = img.get("cls", "")
    print(f"  {src}")
    print(f"    alt={alt[:50]} size={w}x{h} class={cls[:30]}")
    print()

browser.close()
playwright.stop()
chrome_process.kill()
