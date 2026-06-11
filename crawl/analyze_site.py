"""
Analyze the Zomi worship site structure — finds how songs are loaded.
"""
from playwright.sync_api import sync_playwright
import time, json, os

DEBUG_PORT = 9333
CHROME_PATH = "/usr/bin/chromium"
USER_DATA_DIR = os.path.expanduser("~/.config/chromium")

def analyze_site():
    import subprocess
    subprocess.run(["pkill", "-f", f"chromium.*{DEBUG_PORT}"], capture_output=True)
    time.sleep(1)

    proc = subprocess.Popen(
        [CHROME_PATH, f"--remote-debugging-port={DEBUG_PORT}",
         f"--user-data-dir={USER_DATA_DIR}",
         "--no-first-run", f"--window-size=1280,900",
         "https://zomiworshipcollective.com/lyrics/category-tedim-labu/"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{DEBUG_PORT}")
        page = browser.contexts[0].pages[0]

        print("Page loaded. Waiting 10s for Cloudflare...")
        time.sleep(10)

        # Get full page HTML  
        html = page.content()
        
        # Look for WordPress REST API data or embedded song data
        import re
        
        # Check for wp-json API calls
        api_patterns = re.findall(r'wp-json[^"\']+', html)
        if api_patterns:
            print(f"WP API URLs found: {api_patterns[:5]}")
        
        # Look for JSON data (song data)
        json_data = re.findall(r'<script[^>]+type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)
        print(f"\nJSON scripts found: {len(json_data)}")
        for jd in json_data[:3]:
            print(f"  JSON data: {len(jd)} chars")
            # Check if it contains song/lyric data
            if '"lyric"' in jd or '"song"' in jd or 'lyrics' in jd[:500]:
                print(f"  Has lyric data!")
                parsed = json.loads(jd)
                print(f"  Keys: {list(parsed.keys())[:10]}")
        
        # Look for all link elements with song titles
        all_links = page.query_selector_all("a")
        song_links = []
        for link in all_links:
            href = link.get_attribute("href") or ""
            text = link.inner_text().strip()
            if '/lyrics/' in href and '/category-' not in href:
                song_links.append((text[:60], href[:120]))
        
        print(f"\nDirect song links found: {len(song_links)}")
        for t, h in song_links[:10]:
            print(f"  [{t}] {h}")
        
        # Look for any element with onclick that might load lyrics
        onclick_elements = page.query_selector_all("[onclick]")
        print(f"\nElements with onclick: {len(onclick_elements)}")
        for el in onclick_elements[:5]:
            onclick = el.get_attribute("onclick") or ""
            text = el.inner_text().strip()[:50]
            print(f"  [{text}] onclick={onclick[:100]}")
        
        # Monitor network requests for any API calls
        print("\nMonitoring network for 5 seconds...")
        page.evaluate("""
            document.addEventListener('click', function(e) {
                console.log('CLICKED:', e.target.innerText);
            });
        """)
        
        # Try clicking on a song title to see what happens
        # Find elements that look like song titles
        song_elements = page.query_selector_all("[class*='song'], [class*='track'], [class*='title'], [class*='list'] a")
        print(f"\nSong-like elements: {len(song_elements)}")
        
        time.sleep(2)
        
        # Show page text to see song titles
        text = page.inner_text("body")
        lines = [l.strip() for l in text.split('\n') if l.strip() and len(l) > 10]
        print(f"\nText lines: {len(lines)}")
        # Show lines that look like song titles (not navigation)
        for l in lines[:40]:
            if not any(kw in l.lower() for kw in ['cookie', 'privacy', 'cloudflare', 'search', 'menu', 'skip']):
                print(f"  {l[:120]}")

        browser.close()
    proc.kill()

analyze_site()
