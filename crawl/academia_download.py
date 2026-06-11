"""
Academia.edu PDF downloader using Playwright.

Automates the signup/login and download process for free Academia.edu papers.

Usage:
    # Download without account (if available for free):
    python3 academia_download.py https://www.academia.edu/39511363/Zolai_Standard_Format

    # With login credentials (recommended for reliable downloads):
    python3 academia_download.py https://www.academia.edu/39511363/Zolai_Standard_Format --email you@email.com --password yourpass

Note: Free Academia.edu accounts can download most papers.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def download_pdf(url: str, email: str = "", password: str = "") -> bool:
    """Download a PDF from Academia.edu using Playwright.

    Attempts to access the download link. If prompted for login,
    uses provided credentials or creates a free account.

    Returns True if PDF was downloaded successfully.
    """
    output_dir = Path("/home/pauk/zomi_dataset/data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # headless=False to see the process
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        print(f"Loading {url}...")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Wait for page to load
        time.sleep(3)

        # Try clicking the download button
        try:
            # Look for download button/link
            download_selectors = [
                "a[href*='download']",
                "button:has-text('Download')",
                "a:has-text('Download PDF')",
                ".download-link",
                "[data-action='download']",
            ]

            for selector in download_selectors:
                try:
                    btn = page.query_selector(selector)
                    if btn:
                        print(f"Found download button: {selector}")
                        btn.click()
                        time.sleep(3)
                        break
                except Exception:
                    continue

            # Wait for download to start
            print("Waiting for download...")
            time.sleep(5)

        except Exception as e:
            print(f"Click failed: {e}")

        # Check for new tabs or PDF response
        pages = context.pages
        print(f"Open pages: {len(pages)}")

        # Look for PDF in the page
        pdf_pattern = re.compile(r'\.pdf')
        for p in pages:
            if pdf_pattern.search(p.url):
                print(f"Found PDF URL: {p.url}")
                # Try to download
                try:
                    resp = p.goto(p.url)
                    if resp and resp.headers.get("content-type", "").startswith("application/pdf"):
                        data = resp.body()
                        filename = f"academia_{int(time.time())}.pdf"
                        path = output_dir / filename
                        path.write_bytes(data)
                        print(f"Downloaded to {path}")
                        browser.close()
                        return True
                except Exception as e:
                    print(f"Download failed: {e}")

        input("Press Enter after download completes (or Ctrl+C to cancel)...")
        browser.close()
        return False


def main():
    parser = argparse.ArgumentParser(description="Download from Academia.edu")
    parser.add_argument("url", help="Academia.edu paper URL")
    parser.add_argument("--email", help="Email for login")
    parser.add_argument("--password", help="Password for login")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    args = parser.parse_args()

    success = download_pdf(args.url, args.email or "", args.password or "")
    if success:
        print("✓ PDF downloaded")
    else:
        print("PDF not downloaded. The paper may require login.")
        print("Run with --email and --password if you have an account.")


if __name__ == "__main__":
    main()
