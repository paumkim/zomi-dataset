"""
Scribd document text extractor using Playwright (headless Chromium).

Opens a Scribd document URL, renders each page, extracts text from the
text layer, and saves to a file.

Usage:
    python3 scribd_extract.py https://www.scribd.com/document/221579380/Ciamnuih-Laibu
    python3 scribd_extract.py <scribd_url> [--output output.txt] [--pages 10]
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright


def extract_scribd_text(url: str, max_pages: int = 0, timeout: int = 30000) -> str:
    """Open a Scribd document and extract text from rendered pages.

    Scribd renders documents as page images with an overlaid text layer.
    This function waits for the text layer to render and extracts it.

    Args:
        url: Scribd document URL
        max_pages: Max pages to extract (0 = all available)
        timeout: Page load timeout in ms

    Returns:
        Extracted text content
    """
    all_text: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
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
        page.goto(url, wait_until="domcontentloaded", timeout=timeout)

        # Wait for the document viewer to load
        try:
            page.wait_for_selector(".outer_page", timeout=15000)
            print("Document viewer loaded")
        except Exception:
            print("Warning: Document viewer not detected, trying fallback...")

        # Give JavaScript time to render text layers
        time.sleep(5)

        # Try to extract text from all visible text layer elements
        # Scribd uses spans with class names like 'a', 'g', 'l', 'w' inside .text_layer
        text_elements = page.query_selector_all(".text_layer span")
        if text_elements:
            print(f"Found {len(text_elements)} text layer elements")

            # Group by page if possible
            outer_pages = page.query_selector_all(".outer_page")
            print(f"Found {len(outer_pages)} page containers")

            for i, outer in enumerate(outer_pages):
                if max_pages > 0 and i >= max_pages:
                    break

                # Get text from this page's text layer
                page_text_layer = outer.query_selector(".text_layer")
                if page_text_layer:
                    # Get all text spans
                    spans = page_text_layer.query_selector_all("span")
                    page_text_parts: list[str] = []
                    for span in spans:
                        text = span.inner_text().strip()
                        if text:
                            page_text_parts.append(text)

                    if page_text_parts:
                        page_text = " ".join(page_text_parts)
                        all_text.append(page_text)
                        print(f"  Page {i + 1}: {len(page_text)} chars")

        # Fallback: try to get document text from page content
        if not all_text:
            print("Text layer extraction failed, trying body text fallback...")
            body_text = page.inner_text("body")

            # Clean up the extracted text
            lines = [l.strip() for l in body_text.split("\n") if l.strip()]
            # Filter out navigation garbage
            clean_lines = [
                l for l in lines
                if len(l) > 20
                and "Skip to main content" not in l
                and "Sign in" not in l
                and "Search" not in l
                and "Upload" not in l
                and "Menu" not in l
            ]
            all_text.extend(clean_lines)

        browser.close()

    return "\n\n".join(all_text)


def extract_with_navigation(url: str, max_pages: int = 0) -> str:
    """Alternative approach: navigate through pages using Scribd's UI.

    Scribd documents sometimes have a 'page' parameter in the URL that
    can be incremented to load each page individually.
    """
    all_text: list[str] = []
    base_url = re.sub(r"[/#].*$", "", url)

    # Try page URL pattern: /document/<id>/<title>?page=N
    doc_id_match = re.search(r"/document/(\d+)", url)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        loaded_any = False
        page_num = 1
        attempts = 0

        while attempts < (max_pages if max_pages > 0 else 200):
            attempts += 1
            page_url = f"{url}?page={page_num}"

            try:
                print(f"Loading page {page_num}...")
                page.goto(page_url, wait_until="domcontentloaded", timeout=20000)
                time.sleep(3)

                # Try text layer
                text_spans = page.query_selector_all(".text_layer span")
                page_text_parts: list[str] = []
                for span in text_spans:
                    text = span.inner_text().strip()
                    if text:
                        page_text_parts.append(text)

                if page_text_parts:
                    page_text = " ".join(page_text_parts)
                    all_text.append(page_text)
                    print(f"  Extracted {len(page_text)} chars")
                    loaded_any = True
                else:
                    # Try body text
                    body = page.inner_text("body")
                    if body and "page" not in body.lower()[50:100]:
                        all_text.append(body[:2000])
                        print(f"  Body fallback: {len(body[:2000])} chars")

            except Exception as e:
                print(f"  Failed: {e}")

            page_num += 1

        browser.close()

    if not loaded_any:
        print("Warning: No text was successfully extracted.")
        print("The document may require a Scribd login or subscription.")

    return "\n\n".join(all_text)


def main():
    parser = argparse.ArgumentParser(description="Extract text from Scribd documents")
    parser.add_argument("url", help="Scribd document URL")
    parser.add_argument("--output", "-o", default="", help="Output file path")
    parser.add_argument("--pages", "-p", type=int, default=0, help="Max pages to extract")
    parser.add_argument("--nav", action="store_true", help="Use page-by-page navigation method")
    args = parser.parse_args()

    print(f"Extracting text from: {args.url}")

    if args.nav:
        text = extract_with_navigation(args.url, args.pages)
    else:
        text = extract_scribd_text(args.url, args.pages)

    if not text.strip():
        print("\nNo text extracted. The document may require:")
        print("  1. A Scribd login (free account)")
        print("  2. A Scribd subscription")
        print("  3. Or downloading the PDF and using: python3 main.py pdf <file>")
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        # Generate from URL
        doc_id = re.search(r"/document/(\d+)", args.url)
        if doc_id:
            output_path = Path(f"scribd_{doc_id.group(1)}.txt")
        else:
            output_path = Path("scribd_extracted.txt")

    output_path.write_text(text, encoding="utf-8")
    print(f"\nSaved {len(text)} chars to {output_path}")
    print(f"Preview: {text[:200]}...")


if __name__ == "__main__":
    main()
