"""
Zomi Dataset — One-Command Downloader
Usage: python scripts/download_zomi.py
"""

import urllib.request, os, sys
from pathlib import Path

BASE = "https://raw.githubusercontent.com/paumkim/zomi-dataset/main"
FILES = [
    "data/zomi_clean_p1.txt",
    "data/zomi_clean_p2.txt",
    "data/zomi_clean_p3.txt",
    "data/zomi_clean_p4.txt",
    "data/tedim1932_verses.txt",
    "data/tedim1932_normalized.txt",
    "docs/cloud_training_guide.md",
]

out_dir = Path("zomi_dataset")
out_dir.mkdir(exist_ok=True)

print("Downloading Zomi Dataset...")
for path in FILES:
    url = f"{BASE}/{path}"
    dest = out_dir / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        urllib.request.urlretrieve(url, dest)
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  ✓ {path} ({size_mb:.1f} MB)")
    except Exception as e:
        print(f"  ✗ {path}: {e}")

print(f"\nDone! Files saved to {out_dir}/")
