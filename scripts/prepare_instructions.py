"""
Prepare instruction-tuning dataset from Tatoeba parallel data.
Converts translation pairs into instruction format for Phase 2 training.

Output: data/zomi_instructions.jsonl — ready for fine-tuning
"""

import json, glob, os
from pathlib import Path

CACHE = Path.home() / ".cache" / "huggingface" / "hub"
TATOEBA_DIR = "datasets--ZomiLearner--English-Zomi-OPUS_Tatoeba_v20230412"
BASE = Path(__file__).parent.parent
OUTPUT = BASE / "data" / "zomi_instructions.jsonl"

INSTRUCTION_EN = "Translate the following English text to Zomi."
INSTRUCTION_ZOMI = "Translate the following Zomi text to English."

def prepare(max_pairs=500000):
    files = sorted(glob.glob(str(CACHE / TATOEBA_DIR / "snapshots" / "*" / "*.jsonl")))
    if not files:
        print("Tatoeba data not found in HF cache.")
        return False

    count = 0
    with open(OUTPUT, "w", encoding="utf-8") as out:
        for f in files:
            with open(f, "r", encoding="utf-8") as fh:
                for line in fh:
                    d = json.loads(line)
                    en = d.get("en", "").strip()
                    zomi = d.get("zomi", "").strip()
                    if not en or not zomi or len(en) < 3 or len(zomi) < 3:
                        continue

                    # Skip if too long for our model
                    if len(en) > 500 or len(zomi) > 500:
                        continue

                    # English → Zomi
                    out.write(json.dumps({
                        "instruction": INSTRUCTION_EN,
                        "input": en,
                        "output": zomi
                    }, ensure_ascii=False) + "\n")
                    count += 1

                    # Zomi → English
                    out.write(json.dumps({
                        "instruction": INSTRUCTION_ZOMI,
                        "input": zomi,
                        "output": en
                    }, ensure_ascii=False) + "\n")
                    count += 1

                    if count >= max_pairs:
                        break
            if count >= max_pairs:
                break

    size_mb = OUTPUT.stat().st_size / (1024 * 1024) if OUTPUT.exists() else 0
    print(f"Created {OUTPUT}")
    print(f"  Total instruction pairs: {count:,}")
    print(f"  File size: {size_mb:.1f} MB")
    print(f"  Format: {{\"instruction\": \"...\", \"input\": \"...\", \"output\": \"...\"}}")
    return True

if __name__ == "__main__":
    prepare()
