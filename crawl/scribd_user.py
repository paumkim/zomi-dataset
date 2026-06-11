"""
Scribd bulk downloader by user.

Downloads ALL documents from a Scribd user's profile page.
Each document is saved as PDF, then OCR'd and added to the dataset.

Usage:
    python3 crawl/scribd_user.py https://www.scribd.com/user/147877536/LTTuang
    python3 crawl/scribd_user.py https://www.scribd.com/user/147877536/LTTuang --skip-ocr
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from bs4 import BeautifulSoup

SCRIBD_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def get_documents_from_profile(url: str) -> list[dict]:
    """Extract document IDs and titles from a Scribd user profile page.

    Uses Playwright to render the page (Scribd loads documents via JS).
    Falls back to basic HTTP if Playwright is unavailable.
    """
    import urllib.request

    docs: list[dict] = []
    seen_ids: set[str] = set()

    # Try Playwright first for JS-rendered content
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=SCRIBD_USER_AGENT)
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(3)

            # Scroll to load lazy content
            for _ in range(5):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)

            html = page.content()
            browser.close()
    except ImportError:
        # Fallback to basic HTTP
        req = urllib.request.Request(url, headers={"User-Agent": SCRIBD_USER_AGENT})
        html = urllib.request.urlopen(req, timeout=15).read().decode()

    soup = BeautifulSoup(html, "html.parser")

    # Extract document IDs from links
    for link in soup.find_all("a", href=True):
        href = link["href"]
        m = re.search(r"/document/(\d+)(?:/([^\"<&?]+))?", href)
        if m:
            doc_id = m.group(1)
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                title = (m.group(2) or link.get_text(strip=True) or "Untitled").replace("-", " ").strip()
                # Clean up image URL titles
                if title.startswith("original/") or not title or len(title) < 3:
                    title = link.get("title", "") or link.get_text(strip=True) or f"Document_{doc_id}"
                docs.append({"id": doc_id, "title": title[:100]})

    return docs


def download_document(doc: dict, output_dir: Path) -> Path | None:
    """Download a single Scribd document using selenium-based downloader."""
    doc_id = doc["id"]
    title = doc["title"]
    safe_title = re.sub(r'[^a-zA-Z0-9]+', '_', title)[:50]

    print(f"\n[{doc_id}] {title}")
    print(f"  Downloading...")

    # Use the existing scribd_downloader.py logic
    try:
        result = subprocess.run(
            [sys.executable, "-c", f"""
import sys, os
sys.path.insert(0, '.')
os.environ['SCRIBD_HEADLESS'] = '1'

from crawl.scribd_downloader import convert_scribd_link, get_filename_from_url
from crawl.scribd_downloader import build_chrome_options, scroll_through_pages
from crawl.scribd_downloader import hide_cookie_dialogs, prepare_document_for_print
from crawl.scribd_downloader import inject_print_styles, wait_for_render_stability
from crawl.scribd_downloader import detect_document_paper_size, save_pdf_directly

import tempfile, time
from selenium import webdriver

url = "https://www.scribd.com/document/{doc_id}/{title}"
converted = convert_scribd_link(url)
if converted == 'Invalid Scribd URL':
    print('INVALID URL')
    sys.exit(1)

pdf_name = "{safe_title}.pdf"
pdf_path = os.path.join(r'{output_dir}', pdf_name)

with tempfile.TemporaryDirectory(prefix='scribd-') as profile:
    opts = build_chrome_options(profile)
    driver = webdriver.Chrome(options=opts)
    try:
        driver.get(converted)
        time.sleep(1)
        hide_cookie_dialogs(driver)
        pages = scroll_through_pages(driver, 0.15)
        if pages == 0:
            print('NO PAGES')
            sys.exit(1)
        prepare_document_for_print(driver)
        inject_print_styles(driver)
        wait_for_render_stability(driver, 15)
        paper = detect_document_paper_size(driver)
        saved = save_pdf_directly(driver, pdf_path, paper_size=paper)
        if saved:
            print(f'PDF: {{saved}}')
        else:
            print('FAILED')
    finally:
        driver.quit()
            """],
            capture_output=True, text=True, timeout=600,
            cwd=Path(__file__).resolve().parent.parent,
        )

        # Extract PDF path from output
        for line in result.stdout.split("\n"):
            if line.startswith("PDF: "):
                pdf_path = line[5:].strip()
                return Path(pdf_path)
            if "FAILED" in line or "INVALID URL" in line or "NO PAGES" in line:
                print(f"  Failed: {line}")
                return None

        print(f"  Output: {result.stdout[-300:]}")
        if result.stderr:
            print(f"  Errors: {result.stderr[:200]}")

    except subprocess.TimeoutExpired:
        print(f"  Timeout (10 min)")
    except Exception as e:
        print(f"  Error: {e}")

    return None


def main():
    parser = argparse.ArgumentParser(description="Download all Scribd documents from a user")
    parser.add_argument("url", help="Scribd user profile URL")
    parser.add_argument("--skip-ocr", action="store_true", help="Skip OCR step")
    parser.add_argument("--list-only", action="store_true", help="Only list documents, don't download")
    args = parser.parse_args()

    # Step 1: Get all documents
    print(f"Fetching documents from: {args.url}")
    docs = get_documents_from_profile(args.url)
    print(f"\nFound {len(docs)} documents:")

    for i, doc in enumerate(docs, 1):
        print(f"  {i:2d}. [{doc['id']}] {doc['title'][:70]}")

    if args.list_only:
        return

    # Step 2: Download each document
    output_dir = Path("/home/pauk/zomi_dataset/data/scribd/user_downloads")
    output_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    for doc in docs:
        pdf_path = download_document(doc, output_dir)
        if pdf_path:
            downloaded += 1
            print(f"  ✓ Saved to {pdf_path.name}")
        # Brief pause between downloads
        time.sleep(2)

    print(f"\nDownloaded {downloaded}/{len(docs)} documents to {output_dir}")
    print(f"\nTo process them:")
    print(f"  cd /home/pauk/zomi_dataset")
    print(f"  for f in data/scribd/user_downloads/*.pdf; do python3 main.py pdf \"\$f\"; done")
    print(f"  python3 main.py normalize")
    print(f"  python3 main.py detect")
    print(f"  python3 main.py stats")


if __name__ == "__main__":
    main()
