"""
Crawl all Zomi articles from zomipedia.org via WordPress REST API.
"""
import json
import urllib.request
import re
import time
from pathlib import Path

API_BASE = "https://zomipedia.org/wp-json/wp/v2/posts"
OUTPUT = Path("/home/pauk/zomi_dataset/data/zomipedia_raw.txt")
DELAY = 0.5  # seconds between requests

def fetch_json(url):
    """Fetch and parse JSON from a URL."""
    req = urllib.request.Request(url, headers={"User-Agent": "ZomiDatasetCollector/1.0"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def strip_html(text):
    """Remove HTML tags and entities from text."""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&[a-z]+;', ' ', text)
    text = re.sub(r'&#x[0-9a-fA-F]+;', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# Get total posts
first = fetch_json(f"{API_BASE}?per_page=1&_fields=id")
req = urllib.request.Request(f"{API_BASE}?per_page=1&_fields=id",
                              headers={"User-Agent": "ZomiDatasetCollector/1.0"})
with urllib.request.urlopen(req) as resp:
    total = int(resp.headers.get("X-WP-Total", 0))

print(f"Total posts: {total}")

all_texts = []
page = 1
per_page = 20
fetched = 0

while fetched < total:
    url = f"{API_BASE}?per_page={per_page}&page={page}&_fields=id,title,content"
    try:
        posts = fetch_json(url)
    except Exception as e:
        print(f"  Error on page {page}: {e}")
        time.sleep(2)
        continue

    if not posts:
        break

    for post in posts:
        # Extract title
        title = post.get("title", {}).get("rendered", "")
        title = strip_html(title)

        # Extract content
        content = post.get("content", {}).get("rendered", "")
        content = strip_html(content)

        if title and len(title) > 5:
            all_texts.append(title)
        if content:
            # Split into paragraphs
            for para in re.split(r'\s{2,}', content):
                if len(para) > 30:
                    all_texts.append(para)

        fetched += 1

    print(f"  Page {page}: {len(posts)} posts (total: {fetched}/{total})")
    page += 1
    time.sleep(DELAY)

# Save
OUTPUT.write_text('\n'.join(all_texts), encoding='utf-8')
print(f"\nDone! {len(all_texts)} text chunks saved to {OUTPUT}")
print(f"Total chars: {sum(len(t) for t in all_texts):,}")
