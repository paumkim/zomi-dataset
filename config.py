"""
Zomi Dataset Collector — Configuration.
"""
from pathlib import Path

ROOT = Path(__file__).parent

# Directories
DATA_RAW = ROOT / "data" / "raw"
DATA_TEXTS = ROOT / "data" / "texts"
DATA_ZOMI = ROOT / "data" / "zomi_only"
DATA_DATASET = ROOT / "data" / "dataset"
DATA_SEEDS = ROOT / "data" / "seeds"
PROFILES_DIR = ROOT / "detect" / "profiles"

# Language detection
ZOMI_THRESHOLD = 0.4       # Minimum Zomi score to accept
OTHER_THRESHOLD = 0.5      # Maximum other language score allowed
MIN_PARAGRAPH_LENGTH = 20  # Skip paragraphs shorter than this

# Normalization
# Patterns: (regex pattern, replacement)
# Applied in order — first match wins
MERGE_RULES = [
    # Merge standalone particles to preceding word
    (r'\b(pa)\b', ''),      # Remove standalone "pa" (it was merged above)
    (r'\b(pi)\b', ''),      # Remove standalone "pi"
    (r'\b(in)\b', ''),      # Remove standalone "in" (context-dependent)
    # These need smarter handling — see normalizer.py
]

# Crawl settings
CRAWL_DELAY = 1.5       # Seconds between requests (politeness)
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ZomiDatasetCollector/1.0"
