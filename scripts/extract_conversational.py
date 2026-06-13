"""
Extract conversational Zomi from within the Bible text.
Even the Bible has dialog — questions, quotes, direct speech.
These sound more natural than narrative verses.
Output: data/conversational_zomi.txt
"""

import re
from pathlib import Path

BASE = Path(__file__).parent.parent
CORPUS = BASE / "data" / "zomi_clean_p1.txt"  # Gospels are here (Matthew, Mark, Luke, John)
OUTPUT = BASE / "data" / "conversational_zomi.txt"
YOUTUBE_FILES = [
    BASE / "data" / "youtube_casual_zomi.txt",
    BASE / "data" / "youtube_zomi.txt",
    BASE / "data" / "youtube_zomi_new.txt",
]

# Zomi conversational patterns — direct speech markers
SPEECH_MARKS = ['"', '"', '"', '"', '"', '"', '"', '"']

def is_conversational(line):
    """Check if a line contains conversational elements."""
    # Direct speech (quotes)
    if any(m in line for m in ['"', '"', '"', '"']):
        return True
    # Questions
    if "?" in line or "hiam" in line.lower().split()[-1]:
        return True
    # Greetings and commands
    if line.lower().startswith(("hello", "hi ", "damma", "dammaw", "un", "te", "note")):
        return True
    # Short lines (conversations tend to be shorter)
    words = line.split()
    if 3 <= len(words) <= 15:
        return True
    return False

def extract():
    lines = []

    # Extract conversational lines from Bible corpus
    print("Scanning Bible for conversational passages...")
    with open(CORPUS, "r", encoding="utf-8", errors="ignore") as f:
        bible_lines = [l.strip() for l in f if l.strip()]

    conversational = [l for l in bible_lines if is_conversational(l)]
    print(f"  Found {len(conversational):,} conversational-style lines in Bible")
    lines.extend(conversational[:5000])  # Keep top 5k

    # Extract from YouTube
    for ytf in YOUTUBE_FILES:
        if ytf.exists():
            with open(ytf, "r", encoding="utf-8", errors="ignore") as f:
                yt_lines = [l.strip() for l in f if l.strip() and len(l) > 10]
            lines.extend(yt_lines[:500])
            print(f"  Added {len(yt_lines[:500]):,} from {ytf.name}")

    # Write output
    OUTPUT.parent.mkdir(exist_ok=True)
    seen = set()
    with open(OUTPUT, "w", encoding="utf-8") as out:
        for line in lines:
            key = line.lower().strip()[:50]
            if key not in seen:
                seen.add(key)
                out.write(line + "\n")

    print(f"\nSaved {len(seen):,} unique conversational Zomi lines to {OUTPUT.name}")

if __name__ == "__main__":
    extract()
