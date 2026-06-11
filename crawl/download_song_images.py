"""
Download song images from Zomi Worship Collective using real browser.
Resuses the lyrics collector's browser launcher to bypass Cloudflare.
"""
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from crawl.lyrics_collector import launch_real_browser, LYRICS_URL

# Load songs
progress_path = Path(__file__).parent.parent / "crawl" / "lyrics_progress.json"
songs = json.loads(progress_path.read_text()).get("songs", [])
print(f"Total songs: {len(songs)}")

# Output folder
output_dir = Path.home() / "zomi_dataset" / "data" / "song_images"
output_dir.mkdir(parents=True, exist_ok=True)

# Launch real browser
browser, playwright, chrome_process = launch_real_browser()
page = browser.new_page()

downloaded = 0
for i, song in enumerate(songs):
    url = song.get("url", "")
    title = song.get("title", "unknown").replace("/", "_").strip()
    artist = song.get("artist", "unknown").replace("/", "_").strip()
    
    if not url:
        continue
    
    # Create artist subfolder
    artist_dir = output_dir / artist
    artist_dir.mkdir(exist_ok=True)
    
    try:
        page.goto(url, timeout=15000, wait_until="domcontentloaded")
        time.sleep(1)
        
        # Find all images on the page
        images = page.eval_on_selector_all("img", 
            "elements => elements.map(e => ({src: e.src, alt: e.alt, width: e.naturalWidth}))")
        
        for img in images:
            src = img.get("src", "")
            alt = img.get("alt", "")
            w = img.get("width", 0)
            
            # Skip tiny icons, logos, etc. - only get full-size images
            if w < 200:
                continue
            if "logo" in src.lower() or "icon" in src.lower():
                continue
            if "gravatar" in src.lower():
                continue
            
            # Download the image
            try:
                filename = f"{title[:50]}.jpg"
                if "?" in filename:
                    filename = filename.split("?")[0]
                filepath = artist_dir / filename
                
                req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = resp.read()
                    filepath.write_bytes(data)
                
                size_kb = len(data) / 1024
                print(f"  [{i+1}/{len(songs)}] {artist} - {title}: {filename} ({size_kb:.0f} KB)")
                downloaded += 1
            except Exception as e:
                print(f"  [!] {artist} - {title}: download failed - {str(e)[:50]}")
                
    except Exception as e:
        print(f"  [X] {artist} - {title}: page error - {str(e)[:50]}")

print(f"\nDownloaded {downloaded} images to {output_dir}")
browser.close()
playwright.stop()
chrome_process.kill()
