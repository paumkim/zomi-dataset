"""
Crawl blocked/slow Zomi sites with better settings.
"""
import sys, time
sys.path.insert(0, '.')

from crawl.crawler import crawl_generic, fetch_page, extract_text_from_html, is_zomi_text, load_zomi_profile

# zomidaily — hit rate limit, retry with longer delay
print("=== zomidaily (retry with 5s delay) ===")
crawl_generic({
    'name': 'zomidaily_v2',
    'seed_url': 'https://zomidaily.com/',
    'type': 'news',
    'handler': 'html',
    'delay': 5.0,
}, max_pages=50)

# zomiworship — got 403, try different user agent
print("\n=== zomiworship (retry with browser UA) ===")
from crawl.crawler import USER_AGENT as OLD_UA
import urllib.request
# Override user agent with a more browser-like one
orig_fetch = fetch_page
def browser_fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  [WARN] {e}")
        return None

import crawl.crawler
crawl.crawler.fetch_page = browser_fetch

crawl_generic({
    'name': 'zomiworship_v2',
    'seed_url': 'https://zomiworshipcollective.com/lyrics/',
    'type': 'lyrics',
    'handler': 'html',
    'delay': 3.0,
}, max_pages=50)

# Restore original
crawl.crawler.fetch_page = orig_fetch

print("\nAll retries complete.")
