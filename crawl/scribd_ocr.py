"""
Download Scribd document page images and OCR them.

Scribd renders documents as page images on their CDN.
This script downloads each page image and runs Tesseract OCR
to extract the text.

Usage:
    python3 scribd_ocr.py https://www.scribd.com/document/221579380/Ciamnuih-Laibu
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import time
import urllib.request
from pathlib import Path


# Scribd page image URL pattern
# Page 1: https://imgv2-2-f.scribdassets.com/img/document/<DOC_ID>/original/<HASH>/1?v=1
# Page 2: https://imgv2-2-f.scribdassets.com/img/document/<DOC_ID>/original/<HASH>/2?v=1


def get_doc_info(url: str) -> dict:
    """Extract document ID and page count from the Scribd page."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=15).read().decode()

    # Extract document ID
    doc_id = ""
    id_match = re.search(r'img/document/(\d+)/original/', html)
    if id_match:
        doc_id = id_match.group(1)

    # Extract hash from cover image URL
    oc_match = re.search(r'img/document/\d+/original/([a-f0-9]+)/', html)
    doc_hash = oc_match.group(1) if oc_match else ""

    # Extract page count
    pages = 0
    pg_match = re.search(r'(\d+)\s*pages', html, re.IGNORECASE)
    if pg_match:
        pages = int(pg_match.group(1))

    # Try another pattern for page count
    if not pages:
        pg_match = re.search(r'Pages[:\s]+(\d+)', html)
        if pg_match:
            pages = int(pg_match.group(1))

    # Extract title
    title = ""
    t_match = re.search(r'<title>(.*?)</title>', html)
    if t_match:
        title = t_match.group(1).strip()

    print(f"Document ID: {doc_id}")
    print(f"Hash: {doc_hash}")
    print(f"Pages: {pages}")
    print(f"Title: {title}")

    return {"id": doc_id, "hash": doc_hash, "pages": pages, "title": title}


def download_page_images(doc_id: str, doc_hash: str, page_count: int, output_dir: Path) -> list[Path]:
    """Download all page images from Scribd's CDN."""
    os.makedirs(output_dir, exist_ok=True)
    image_paths: list[Path] = []

    print(f"\nDownloading {page_count} pages...")
    for page_num in range(1, page_count + 1):
        # Try multiple CDN subdomains (0, 1, 2) in case some are blocked
        img_urls = [
            f"https://imgv2-2-f.scribdassets.com/img/document/{doc_id}/original/{doc_hash}/{page_num}?v=1",
        ]

        downloaded = False
        for img_url in img_urls:
            try:
                req = urllib.request.Request(img_url, headers={
                    "User-Agent": "Mozilla/5.0",
                    "Referer": "https://www.scribd.com/",
                })
                data = urllib.request.urlopen(req, timeout=30).read()

                ext = "png"
                if data[:4] == b"\xff\xd8\xff\xe0":
                    ext = "jpg"
                elif data[:4] == b"\x89PNG":
                    ext = "png"

                img_path = output_dir / f"page_{page_num:04d}.{ext}"
                img_path.write_bytes(data)
                image_paths.append(img_path)

                if page_num % 10 == 0 or page_num == page_count:
                    print(f"  Page {page_num}/{page_count} downloaded")
                downloaded = True
                break
            except Exception as e:
                print(f"  Page {page_num} failed: {e}")

        # Brief delay between downloads
        time.sleep(1)

    return image_paths


def ocr_images(image_paths: list[Path], output_dir: Path) -> str:
    """Run Tesseract OCR on all page images."""
    ocr_dir = output_dir / "ocr_pages"
    os.makedirs(ocr_dir, exist_ok=True)

    all_text: list[str] = []

    print(f"\nRunning OCR on {len(image_paths)} pages...")
    for i, img_path in enumerate(image_paths):
        page_num = i + 1
        ocr_output = ocr_dir / f"page_{page_num:04d}"

        try:
            subprocess.run(
                ["tesseract", str(img_path), str(ocr_output),
                 "-l", "eng+mya", "--psm", "6"],
                capture_output=True, text=True, timeout=60,
            )

            txt_path = ocr_output.with_suffix(".txt")
            if txt_path.exists():
                page_text = txt_path.read_text(encoding="utf-8", errors="ignore")
                all_text.append(f"--- Page {page_num} ---\n{page_text.strip()}")

                if page_num % 10 == 0 or page_num == len(image_paths):
                    print(f"  Page {page_num}/{len(image_paths)} OCR'd")
        except Exception as e:
            print(f"  Page {page_num} OCR failed: {e}")
            all_text.append(f"--- Page {page_num} ---\n[OCR FAILED]")

        # Brief delay
        time.sleep(0.5)

    return "\n\n".join(all_text)


def main():
    parser = argparse.ArgumentParser(description="OCR Scribd documents")
    parser.add_argument("url", help="Scribd document URL")
    parser.add_argument("--output", "-o", default="", help="Output text file")
    parser.add_argument("--max-pages", "-p", type=int, default=0, help="Limit pages")
    args = parser.parse_args()

    # Get document info
    info = get_doc_info(args.url)
    if not info["id"] or not info["hash"]:
        print("Could not extract document info. URL may be invalid.")
        return

    if args.max_pages > 0:
        info["pages"] = min(info["pages"], args.max_pages)

    # Create output directories
    safe_name = re.sub(r'[^a-zA-Z0-9]+', '_', info["title"][:30]) or f"scribd_{info['id']}"
    output_dir = Path("data/scribd") / safe_name
    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Download page images
    image_paths = download_page_images(info["id"], info["hash"], info["pages"], output_dir / "images")
    if not image_paths:
        print("No images downloaded. Document may require subscription.")
        return

    # Step 2: OCR
    full_text = ocr_images(image_paths, output_dir)

    # Step 3: Save
    output_path = args.output or f"{safe_name}.txt"
    Path(output_path).write_text(full_text, encoding="utf-8")

    print(f"\nDone! Saved {len(full_text)} chars to {output_path}")
    print(f"Pages: {info['pages']}, OCR'd: {len([l for l in full_text.split('\\n') if l.strip()])} lines")


if __name__ == "__main__":
    main()
