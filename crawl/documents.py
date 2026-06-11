"""
Handler for Scribd.com and Academia.edu content.

These sites require login and serve documents as PDFs or embedded viewers.
This module provides tools to process documents once the user provides:
  1. Direct PDF URLs
  2. Or downloaded PDF files
"""
from __future__ import annotations

import json
import re
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

from config import USER_AGENT, DATA_RAW, DATA_TEXTS, DATA_ZOMI


# Known Zomi documents on Scribd
SCRIBD_ZOMI_DOCUMENTS = [
    {
        "title": "Zomi Laibu Zabatts Vol 1",
        "url": "https://www.scribd.com/doc/312130070/Zomi-Laibu-Zabatts-Vol-1",
        "type": "book",
    },
    {
        "title": "Zo Leh Shing Minamte Thu",
        "url": "https://www.scribd.com/doc/282247220/Zo-Leh-Shing-Minamte-Thu",
        "type": "book",
    },
]

# Known Zomi documents on Academia.edu
ACADEMIA_ZOMI_DOCUMENTS = [
    {
        "title": "Zolai Khanggui AD 1899 AD 2013",
        "url": "https://www.academia.edu/39512033/Zolai_Khanggui_AD_1899_AD_2013_",
        "type": "paper",
    },
    {
        "title": "Zolai Standard Format",
        "url": "https://www.academia.edu/39511363/Zolai_Standard_Format",
        "type": "paper",
    },
]


def download_pdf(url: str, output_path: Path) -> bool:
    """Download a PDF from a URL. Works if the URL is a direct PDF link."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            # Check if it's actually a PDF
            if data[:4] == b'%PDF':
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(data)
                return True
            return False
    except Exception as e:
        print(f"  [WARN] Failed to download {url}: {e}")
        return False


def extract_pdf_text(pdf_path: Path, output_path: Path) -> bool:
    """Extract text from a PDF using pdftotext."""
    if not pdf_path.exists():
        return False

    # Check if pdftotext is available
    if subprocess.run(["which", "pdftotext"], capture_output=True).returncode != 0:
        print("pdftotext not found. Install with: sudo apt install poppler-utils")
        return False

    result = subprocess.run(
        ["pdftotext", str(pdf_path), str(output_path)],
        capture_output=True, text=True
    )
    return result.returncode == 0


def process_scribd_document(doc: dict) -> bool:
    """Download and process a Scribd document.

    Note: Scribd requires authentication for full downloads.
    This function attempts to download the preview text.
    """
    print(f"\n[Scribd] Processing: {doc['title']}")
    print(f"  URL: {doc['url']}")
    print(f"  NOTE: Scribd requires login for full downloads.")
    print(f"  If you have a Scribd account, download the PDF manually")
    print(f"  and place it in data/raw/scribd_{doc['title'][:20].replace(' ', '_')}.pdf")
    print(f"  Then run: python main.py process")
    return False


def process_academia_document(doc: dict) -> bool:
    """Download and process an Academia.edu document.

    Academia.edu allows direct PDF downloads from paper pages.
    """
    print(f"\n[Academia] Processing: {doc['title']}")
    print(f"  URL: {doc['url']}")

    # Try to find the PDF download link on the page
    req = urllib.request.Request(doc['url'], headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  [WARN] Failed to fetch page: {e}")
        return False

    # Look for PDF download links
    pdf_urls = re.findall(r'https?://[^"\']+\.pdf', html)
    if not pdf_urls:
        print("  No direct PDF link found. Download manually from the page.")
        return False

    pdf_url = pdf_urls[0]
    pdf_path = DATA_RAW / f"academia_{doc['title'][:20].replace(' ', '_')}.pdf"
    text_path = DATA_TEXTS / f"academia_{doc['title'][:20].replace(' ', '_')}.txt"

    print(f"  Downloading PDF from {pdf_url}...")
    if download_pdf(pdf_url, pdf_path):
        print(f"  Extracting text...")
        if extract_pdf_text(pdf_path, text_path):
            print(f"  ✓ Saved to {text_path}")
            return True

    return False


def process_scribd_all() -> int:
    """Process all known Scribd Zomi documents."""
    count = 0
    for doc in SCRIBD_ZOMI_DOCUMENTS:
        if process_scribd_document(doc):
            count += 1
    return count


def process_academia_all() -> int:
    """Process all known Academia.edu Zomi documents."""
    count = 0
    for doc in ACADEMIA_ZOMI_DOCUMENTS:
        if process_academia_document(doc):
            count += 1
    return count


def process_manual_pdf(pdf_path: Path) -> bool:
    """Process a manually downloaded PDF file."""
    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        print(f"File not found or not a PDF: {pdf_path}")
        return False

    text_path = DATA_TEXTS / f"{pdf_path.stem}.txt"
    print(f"Extracting text from {pdf_path.name}...")
    if extract_pdf_text(pdf_path, text_path):
        size = len(text_path.read_text(encoding="utf-8", errors="ignore"))
        print(f"✓ Saved {size} chars to {text_path}")
        return True
    return False
