"""
Zomi YouTube Comment Miner — extracts Zomi comments from YouTube videos.
No API key needed — uses yt-dlp (free, open source).

Usage:
  python3 scripts/youtube_zomi.py "https://youtube.com/watch?v=VIDEO_ID"
  python3 scripts/youtube_zomi.py --search "Zomi worship song"
  python3 scripts/youtube_zomi.py --search "Tedim" --max 20
"""

import sys, re, json, os, subprocess, time
from pathlib import Path

BASE = Path(__file__).parent.parent
OUTPUT = BASE / "data" / "youtube_zomi_new.txt"
CACHE = BASE / "data" / "youtube_cache.json"

# Zomi markers to detect the language
ZOMI_MARKERS = {"hi", "pen", "in", "tawh", "leh", "mah", "zong", "kei", "Pasian", "Topa",
                "ciang", "bang", "mahmah", "hiam", "hong", "khempeuh", "zaw", "tampi", "mite",
                "ciangin", "bangin", "tua", "ahi", "om", "nawn", "lo"}

def is_zomi(text):
    words = set(text.lower().split())
    matches = words & ZOMI_MARKERS
    return len(matches) >= 2

def search_youtube(query, max_results=10):
    """Search YouTube using yt-dlp (no API key)."""
    try:
        r = subprocess.run(
            ["yt-dlp", f"ytsearch{max_results}:{query}", "--dump-json", "--no-download"],
            capture_output=True, text=True, timeout=30)
        videos = []
        for line in r.stdout.strip().split("\n"):
            if line:
                try:
                    d = json.loads(line)
                    videos.append({
                        "id": d["id"],
                        "title": d["title"],
                        "url": f"https://youtube.com/watch?v={d['id']}",
                        "channel": d.get("channel", ""),
                    })
                except:
                    pass
        return videos
    except FileNotFoundError:
        return None  # yt-dlp not installed
    except Exception as e:
        return []

def get_comments(video_url, max_comments=100):
    """Get comments from a YouTube video using yt-dlp."""
    try:
        r = subprocess.run(
            ["yt-dlp", "--no-download", "--dump-json", "--write-comments",
             "--max-comments", str(max_comments), video_url],
            capture_output=True, text=True, timeout=120)
        comments = []
        for line in r.stdout.strip().split("\n"):
            if line:
                try:
                    d = json.loads(line)
                    if "comment" in d:
                        comments.append(d["comment"])
                except:
                    pass
        return comments
    except Exception as e:
        return []

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    # Check yt-dlp
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, timeout=5)
    except FileNotFoundError:
        print("yt-dlp not found. Install: pip install yt-dlp")
        return

    max_videos = 5
    args = sys.argv[1:]

    if "--search" in args:
        idx = args.index("--search")
        query = args[idx + 1]
        if "--max" in args:
            max_videos = int(args[args.index("--max") + 1])
    elif args[0].startswith("http"):
        # Single video URL
        print(f"Getting comments from: {args[0]}")
        comments = get_comments(args[0])
        zomi_comments = [c for c in comments if is_zomi(c)]
        if zomi_comments:
            with open(OUTPUT, "a", encoding="utf-8") as f:
                for c in zomi_comments:
                    f.write(c.strip() + "\n")
            print(f"Saved {len(zomi_comments)} Zomi comments to {OUTPUT}")
        else:
            print(f"No Zomi comments found in {len(comments)} total comments")
        return

    # Search mode
    videos = search_youtube(args[0] if not args[0].startswith("--") else query, max_videos)

    if videos is None:
        print("yt-dlp not installed. Install: pip install yt-dlp")
        return

    print(f"Found {len(videos)} videos for: {query}")
    all_zomi = 0

    for v in videos:
        print(f"\n  {v['title'][:60]}")
        comments = get_comments(v["url"])
        zomi_comments = [c for c in comments if is_zomi(c)]

        if zomi_comments:
            print(f"  → {len(zomi_comments)} Zomi comments")
            with open(OUTPUT, "a", encoding="utf-8") as f:
                for c in zomi_comments:
                    f.write(c.strip() + "\n")
            all_zomi += len(zomi_comments)
        else:
            print(f"  → No Zomi comments")

        time.sleep(1)  # Be polite

    print(f"\n✅ Saved {all_zomi} Zomi comments to {OUTPUT}")
    print(f"   Total file size: {OUTPUT.stat().st_size if OUTPUT.exists() else 0} bytes")

if __name__ == "__main__":
    main()
