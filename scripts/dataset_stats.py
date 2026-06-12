"""
Zomi Dataset Statistics — run: python scripts/dataset_stats.py
"""

import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
CORPUS_FILES = ["zomi_clean_p1.txt", "zomi_clean_p2.txt", "zomi_clean_p3.txt", "zomi_clean_p4.txt"]

def count_lines_chars(path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    words = text.split()
    return len(lines), len(text), len(words)

total_lines = 0
total_chars = 0
total_words = 0

print("=" * 50)
print("Zomi Dataset Statistics")
print("=" * 50)

for fn in CORPUS_FILES:
    path = DATA / fn
    if path.exists():
        lines, chars, words = count_lines_chars(path)
        total_lines += lines
        total_chars += chars
        total_words += words
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"\n  {fn}:")
        print(f"    Lines:     {lines:>8,}")
        print(f"    Words:     {words:>8,}")
        print(f"    Chars:     {chars:>9,}")
        print(f"    Size:      {size_mb:>5.1f} MB")

print(f"\n{'─' * 50}")
print(f"  TOTAL:")
print(f"    Lines:     {total_lines:>8,}")
print(f"    Words:     {total_words:>8,}")
print(f"    Chars:     {total_chars:>9,}")
print(f"    Files:     {len(CORPUS_FILES):>8,}")

# Unique words across all files
print(f"\n  Unique words (sampled): counting...")
all_words = set()
for fn in CORPUS_FILES:
    path = DATA / fn
    if path.exists():
        text = path.read_text(encoding="utf-8", errors="ignore")
        all_words.update(text.lower().split())
print(f"    Unique:    {len(all_words):>8,}")

print(f"\n{'=' * 50}")
