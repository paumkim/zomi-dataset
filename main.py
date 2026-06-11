"""
Zomi Dataset Collector — main pipeline.

Usage:
    python main.py extract           # Extract Tedim Bible PDF to text
    python main.py normalize         # Normalize all text files
    python main.py crawl             # Crawl TongDot.com dictionary
    python main.py detect            # Build Zomi language profile
    python main.py process           # Run full pipeline
    python main.py dump <folder>     # Process a folder of dumped text files
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from config import DATA_RAW, DATA_TEXTS, DATA_ZOMI, DATA_DATASET, DATA_SEEDS, ROOT



def cmd_extract():
    """Extract Tedim Bible PDF to raw text."""
    pdf_path = Path("/home/pauk/Documents/ChinTedim-All-Bible.pdf")
    if not pdf_path.exists():
        print(f"PDF not found at {pdf_path}")
        return

    output_path = DATA_RAW / "tedim_bible.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if pdftotext is available
    if subprocess.run(["which", "pdftotext"], capture_output=True).returncode != 0:
        print("pdftotext not found. Install with: sudo apt install poppler-utils")
        return

    result = subprocess.run(
        ["pdftotext", str(pdf_path), str(output_path)],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        lines = len(output_path.read_text().split("\n")) if output_path.exists() else 0
        print(f"Extracted {lines} lines to {output_path}")
    else:
        print(f"Extraction failed: {result.stderr}")


def cmd_normalize():
    """Normalize all raw text files and save to zomi_only/."""
    from normalize.normalizer import batch_normalize, _strip_headers, _merge_particles

    sources = list(DATA_RAW.glob("*.txt")) + list(DATA_TEXTS.glob("*.txt")) + list(DATA_TEXTS.glob("*.jsonl"))
    if not sources:
        print("No text files found in data/raw/ or data/texts/")
        print("Extract the Bible first: python main.py extract")
        print("Or dump files into data/texts/")
        return

    total_original = 0
    total_output = 0

    for src in sources:
        output_path = DATA_ZOMI / f"normalized_{src.stem}.txt"
        stats = batch_normalize(src, output_path)
        total_original += stats["original_lines"]
        total_output += stats["output_lines"]
        print(f"  {src.name}: {stats['original_lines']} → {stats['output_lines']} lines (removed {stats['removed']})")

    print(f"\nTotal: {total_original} → {total_output} lines")
    print(f"Saved to {DATA_ZOMI}/")

    # Also process the TongDot dictionary if it exists
    dict_path = DATA_DATASET / "tongdot_dictionary.jsonl"
    if dict_path.exists():
        print("\nNormalizing TongDot dictionary entries...")
        entries = []
        with open(dict_path) as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))

        # Normalize each Zomi entry
        normalized_entries = []
        for entry in entries:
            entry["zomi_normalized"] = _merge_particles(entry.get("zomi", ""))
            normalized_entries.append(entry)

        output_dict = DATA_DATASET / "tongdot_dictionary_normalized.jsonl"
        with open(output_dict, "w", encoding="utf-8") as f:
            for e in normalized_entries:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        print(f"Normalized {len(normalized_entries)} dictionary entries to {output_dict}")


def cmd_crawl():
    """Crawl Zomi websites. Use --site to crawl a specific site."""
    import sys as _sys

    # Check if a specific site was requested
    site = None
    if "--site" in _sys.argv:
        idx = _sys.argv.index("--site")
        if idx + 1 < len(_sys.argv):
            site = _sys.argv[idx + 1]

    from crawl.crawler import crawl_site, crawl_all

    if site:
        print(f"\nCrawling site: {site}")
        crawl_site(site)
    else:
        print("=" * 60)
        print("Crawling ALL Zomi websites")
        print("=" * 60)
        print("Sites:")
        from crawl.crawler import SITES
        for s in SITES:
            print(f"  - {s['name']}: {s['seed_url']}")
        print()
        crawl_all()


def cmd_detect():
    """Build Zomi language profile from seed data and normalized texts."""
    print("Building Zomi character n-gram profile...")

    # Collect all Zomi seed texts
    seed_text = ""
    for f in DATA_SEEDS.glob("*.txt"):
        if f.exists():
            seed_text += f.read_text(encoding="utf-8", errors="ignore") + "\n"

    # Also use normalized Zomi texts
    for f in DATA_ZOMI.glob("*.txt"):
        if f.exists():
            seed_text += f.read_text(encoding="utf-8", errors="ignore") + "\n"

    # Also use the Google Sheet exports if they're in seeds
    sheet1 = DATA_SEEDS / "zomi_sheet1.csv"
    if sheet1.exists():
        import csv
        with open(sheet1, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) > 1 and row[1].strip():
                    seed_text += row[1].strip() + " "

    if not seed_text.strip():
        print("No seed text found. Place Zomi text files in data/seeds/")
        print("Or run: python main.py extract && python main.py normalize")
        return

    # Build character bigram profile
    bigrams = {}
    for i in range(len(seed_text) - 1):
        bigram = seed_text[i:i+2].lower()
        if bigram.isalpha() or "'" in bigram:
            bigrams[bigram] = bigrams.get(bigram, 0) + 1

    # Normalize to frequencies
    total = sum(bigrams.values())
    profile = {k: v / total for k, v in sorted(bigrams.items(), key=lambda x: -x[1])}

    # Save profile
    output_dir = Path("detect/profiles")
    output_dir.mkdir(parents=True, exist_ok=True)
    profile_path = output_dir / "zomi_bigrams.json"
    with open(profile_path, "w") as f:
        json.dump({"bigrams": profile, "total_chars": len(seed_text), "unique_bigrams": len(bigrams)}, f, indent=2)

    print(f"Zomi profile built from {len(seed_text)} characters")
    print(f"  Unique bigrams: {len(bigrams)}")
    print(f"  Top 10 bigrams: {', '.join(k for k, _ in list(profile.items())[:10])}")
    print(f"Saved to {profile_path}")


def cmd_dump():
    """Process a directory of dumped text files."""
    if len(sys.argv) < 3:
        print("Usage: python main.py dump <folder_path>")
        return

    dump_path = Path(sys.argv[2])
    if not dump_path.exists():
        print(f"Path not found: {dump_path}")
        return

    from normalize.normalizer import normalize

    print(f"Processing files in {dump_path}...")
    for f in sorted(dump_path.glob("*.txt")) + sorted(dump_path.glob("*.jsonl")) + sorted(dump_path.glob("*.csv")):
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            normalized = normalize(content)

            if len(normalized.strip()) > 50:  # Skip empty results
                out_path = DATA_ZOMI / f"dump_{f.stem}.txt"
                out_path.write_text(normalized, encoding="utf-8")
                print(f"  {f.name}: {len(content)} → {len(normalized)} chars → saved")
            else:
                print(f"  {f.name}: skipped (too short after normalization)")
        except Exception as e:
            print(f"  {f.name}: error — {e}")


def cmd_process():
    """Run the full pipeline."""
    cmd_extract()
    cmd_normalize()
    cmd_detect()
    print("\nFull pipeline complete.")
    print(f"\nOutput locations:")
    print(f"  Normalized Zomi text: {DATA_ZOMI}/")
    print(f"  TongDot dictionary:   {DATA_DATASET}/")
    print(f"  Zomi profile:         detect/profiles/")


def cmd_docs():
    """Process Scribd and Academia.edu documents."""
    from crawl.documents import process_scribd_all, process_academia_all

    print("Processing Scribd documents...")
    s = process_scribd_all()
    print(f"Done: {s} Scribd documents processed")

    print("\nProcessing Academia.edu documents...")
    a = process_academia_all()
    print(f"Done: {a} Academia documents processed")


def cmd_pdf():
    """Process a manually downloaded PDF file."""
    import sys as _sys, hashlib
    if len(_sys.argv) < 3:
        print("Usage: python main.py pdf <path_to_pdf>")
        return

    pdf_path = Path(_sys.argv[2])
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        return

    # Check if PDF was already processed (via content hash)
    processed_file = Path("data/processed_pdfs.json")
    processed = {}
    if processed_file.exists():
        try:
            processed = json.loads(processed_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    file_hash = hashlib.md5(pdf_path.read_bytes()).hexdigest()
    if file_hash in processed:
        print(f"⏭ Already processed: {pdf_path.name} (was {processed[file_hash]})")
        return

    from crawl.documents import process_manual_pdf
    result = process_manual_pdf(pdf_path)
    if result:
        processed[file_hash] = pdf_path.name
        processed_file.parent.mkdir(parents=True, exist_ok=True)
        processed_file.write_text(json.dumps(processed, indent=2))
        print(f"✓ Marked as processed")


def cmd_stats():
    """Show dataset statistics."""
    zomi_files = list(DATA_ZOMI.glob("*.txt"))
    total_lines = 0
    total_chars = 0
    for f in zomi_files:
        content = f.read_text(encoding="utf-8", errors="ignore")
        lines = len([l for l in content.split("\n") if l.strip()])
        total_lines += lines
        total_chars += len(content)

    dict_files = list(DATA_DATASET.glob("*.jsonl"))
    dict_entries = 0
    for f in dict_files:
        dict_entries += sum(1 for _ in f.open())

    print("=" * 40)
    print("Zomi Dataset Stats")
    print("=" * 40)
    print(f"Normalized text files: {len(zomi_files)}")
    print(f"Total Zomi lines:      {total_lines}")
    print(f"Total Zomi characters: {total_chars:,}")
    print(f"Dictionary entries:    {dict_entries}")
    print(f"Raw files:             {len(list(DATA_RAW.glob('*')))}")
    print(f"Seeds:                 {len(list(DATA_SEEDS.glob('*')))}")
    print("=" * 40)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]
    commands = {
        "extract": cmd_extract,
        "normalize": cmd_normalize,
        "crawl": cmd_crawl,
        "detect": cmd_detect,
        "process": cmd_process,
        "dump": cmd_dump,
        "stats": cmd_stats,
        "docs": cmd_docs,
        "pdf": cmd_pdf,
    }

    if cmd in commands:
        commands[cmd]()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
