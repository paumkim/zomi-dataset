"""
Aggressive Zomi text normalizer.

Merges split particles, removes English headers, standardizes whitespace.

Spelling rules based on native speaker corrections (2026-06):
  - Merge plural te  → mite (not mi te)
  - Merge agentive 'n → Topan (not Topa'n)
  - Merge suffix cing → kicing (not ki cing)
  - Merge berry suffix gah → Singgah (not sing gah)
  - Merge future ding → paaiding (not paai ding)
  - Merge perfective ta → omta (not om ta)
  - Merge locative ah → khawmah (not khawm ah)
  - Merge particles pa, pi, in → Topa, khapi, theiin
  - Keep vowel length distinctions (paai ≠ pai)
  - Keep ia/i, ua/u, aw/o distinct (different words)
  - Keep -ing final (not -in)
  - le (smooth) preferred over leh (aggressive/high-blood-pressure)
"""
from __future__ import annotations

import re
from pathlib import Path


# Particles that should be merged to the preceding word
# NOTE: 'in' is handled by the agentive 'n system instead
MERGE_PARTICLES = {"pa", "pi"}

# Plural marker (like English "s")
MERGE_TE = {"te"}

# Berry/hanging suffix
MERGE_GAH = {"gah"}

# Suffix for readability
MERGE_CING = {"cing"}

# English book/chapter patterns to strip (from Bible headers)
ENGLISH_HEADER_PATTERNS = [
    r"^The\s+\w+\s+Bible.*$",
    r"^\d+\s+(Kings|Samuel|Chronicles|Corinthians|Thessalonians|Timothy|Peter|John).*$",
    r"^\s*(Old|New)\s+Testament\s*$",
    r"^\s*Chin.Tedim\s*-\s*All\s+Bible\s*$",
    r"^\s*Tedim\s*\(Chin\)\s*Bible\s*$",
    r"^\s*©\s*\d+.*$",
    r"^\s*Bible Society of Myanmar.*$",
    r"^\s*Page\s+\d+.*$",
    r"^\s*\d+\s*$",  # Standalone page numbers
]


# Personal info patterns to strip for anonymization
PII_PATTERNS = [
    # Email addresses
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    # Social media handles (@mentions)
    r"@\w+",
    # Blogger/Google profile IDs (long numeric IDs)
    r"blogger\.com/profile/\d+",
    r"blogger\.com,1999:blog-\d+",
    r"(?:www\.)?(?:facebook|instagram|twitter|x)\.com/\w+",
    # Google numeric post/comment IDs (14+ consecutive digits)
    r"\b\d{14,}\b",
    # Google image/content IDs in URLs
    r"blog-\d+\.post-\d+",
    r"/s\d+/[A-Za-z0-9_-]+(?:_n\.jpg|_n\.png)",
    # Blogger/Google URL fragments
    r"tag:blogger\.com,1999:blog-\d+",
    r"noreply@blogger\.com\S*",
    # Timestamps with timezone offsets (blogger format)
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}[-+]\d{2}:\d{2}",
    # Common English footer/noise patterns from crawled content
    r"Continue Reading about [^\n]+",
    r"Read more [^\n]+",
    r"opens in a new window",
    r"opens an external website",
    # Blogger image URLs (base64-like paths and Facebook-style names)
    r"/[A-Za-z0-9_-]{20,}(?:\.jpg|\.png|\.jpeg)",
    r"\b\d+_\d{20,}_n(?:\.jpg|\.png|\.jpeg)",
    # Clean up orphaned URL fragments (http://www. etc.)
    r"https?://(?:www\.)?\S*",
]


def _strip_personal_info(text: str) -> str:
    """Remove emails, social handles, Blogger IDs and other PII."""
    for pattern in PII_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return text


def _expand_hyphenated(text: str) -> str:
    """Expand hyphen/apostrophe-connected particles into separate words.

      "lai-ah" → "lai ah"   (locative)
      "Kherub-te" → "Kherub te" (plural)
      "a'ding" → "a ding"   (for + possessive)
    """
    # Hyphenated particles at end of word or before another hyphen
    text = re.sub(r'-ah\b', ' ah', text)
    text = re.sub(r'-te\b', ' te', text)
    text = re.sub(r'-in\b', ' in', text)
    text = re.sub(r'-ding\b', ' ding', text)
    text = re.sub(r'-ta\b', ' ta', text)
    text = re.sub(r'-cing\b', ' cing', text)
    text = re.sub(r'-gah\b', ' gah', text)
    # Also handle particle-hyphen (e.g., "ah-khat" in "sawm-ah-khat")
    text = re.sub(r'\bah-', ' ah ', text)
    text = re.sub(r'\bte-', ' te ', text)
    text = re.sub(r'\bin-', ' in ', text)
    text = re.sub(r'\bding-', ' ding ', text)
    text = re.sub(r'\bta-', ' ta ', text)

    # Apostrophe-connected particles (word'ding, word'ta, etc.)
    # Expand to space-separated so merge rules can catch them
    text = re.sub(r"(\w+)'ding\b", r'\1 ding', text)
    text = re.sub(r"(\w+)'ta\b", r'\1 ta', text)
    text = re.sub(r"(\w+)'te\b", r'\1 te', text)

    return text


def _merge_reduplication(text: str) -> str:
    """Merge adjacent identical words (reduplication).

      "sem sem" → "semsem"
      "pai pai" → "paipai"
    """
    lines = text.split("\n")
    merged = []
    for line in lines:
        if not line.strip():
            merged.append("")
            continue
        words = line.split()
        result = []
        i = 0
        while i < len(words):
            word = words[i]
            if i + 1 < len(words) and words[i].lower() == words[i + 1].lower():
                result.append(word + words[i + 1])
                i += 2
            else:
                result.append(word)
                i += 1
        merged.append(" ".join(result))
    return "\n".join(merged)


def normalize(text: str) -> str:
    """Main normalization entry point. Applies all rules in order."""
    if not text or not text.strip():
        return ""

    text = text.strip()

    # 0. Expand hyphenated/apostrophe particles so merge rules can catch them
    text = _expand_hyphenated(text)

    # 1. Merge reduplicated words (sem sem → semsem)
    text = _merge_reduplication(text)

    # 2. Strip personal info (emails, social handles, IDs)
    text = _strip_personal_info(text)

    # 3. Fix common Mizoram-influenced spellings to Tedim Zomi standard
    text = re.sub(r'\bToupa\b', 'Topa', text)
    text = re.sub(r'\btoupa\b', 'topa', text)

    # 4. Strip English Bible headers
    text = _strip_headers(text)

    # 3. Merge prefix ki → kicing (ki attaches to following word)
    text = _merge_prefix_ki(text)

    # 4. Merge suffix cing → kicing (before 'in' attaches)
    text = _merge_suffix_cing(text)

    # 5. Merge berry suffix gah → Singgah (not sing gah)
    text = _merge_suffix_gah(text)

    # 6. Merge la (song) → Theila (not thei la)
    text = _merge_la(text)

    # 7. Merge plural te → mite (not mi te)
    text = _merge_plural_te(text)

    # 8. Merge future ding → paaiding (not paai ding)
    text = _merge_ding(text)

    # 9. Merge perfective ta → omta (not om ta)
    text = _merge_ta(text)

    # 10. Merge locative ah → khawmah (not khawm ah)
    text = _merge_ah(text)

    # 11. Merge split particles (pa/pi → attach to preceding word)
    text = _merge_particles(text)

    # 12. Merge agentive 'n → Topa'n (keep apostrophe)
    text = _merge_agentive_n(text)

    # 14. Convert common agentive 'word in' → 'word'n'
    # The 'n form (with apostrophe) is preferred for readability
    text = re.sub(r'\bZeisun\b', "Zeisu'n", text)
    text = re.sub(r'\b(Zeisu|Topa)\s+in\b', r"\1'n", text)
    text = re.sub(r'\bKei\s+in\b', "Ke'n", text)
    text = re.sub(r'\bKein\b', "Ke'n", text)
    text = re.sub(r'\b(Kua|Amah|Ama)\s+in\b', r"\1'n", text)
    text = re.sub(r'\b(Mite|Tate|Note|Kote|Amaute)\s+in\b', r"\1'n", text)
    # Pasian stays as "Pasian in" (separate) — "Pasian'n" is too mouthful

    # 15. Collapse multiple spaces/newlines
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 16. Strip leading/trailing whitespace per line
    lines = [l.strip() for l in text.split("\n")]
    text = "\n".join(l for l in lines if l)

    return text.strip()


def _strip_headers(text: str) -> str:
    """Remove English Bible section headers and chapter numbers."""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Skip if matches any header pattern
        skip = False
        for pattern in ENGLISH_HEADER_PATTERNS:
            if re.match(pattern, stripped, re.IGNORECASE):
                skip = True
                break
        # Skip short numeric lines (chapter numbers like "1", "2")
        if stripped.isdigit() and len(stripped) <= 3:
            continue
        # Skip lines that are clearly English (matches known English-only patterns)
        if not skip and stripped:
            words = stripped.split()
            # Only strip if the line has VERY long words (8+ chars) typical of English
            # and almost no short words typical of Zomi
            if len(words) >= 5:
                long_ascii = sum(1 for w in words if re.match(r'^[A-Za-z]{8,}$', w))
                short_zomi = sum(1 for w in words if len(w) <= 3)
                if long_ascii >= len(words) * 0.5 and short_zomi == 0:
                    continue
        if not skip:
            cleaned.append(stripped)
    return "\n".join(cleaned)


def _merge_particles(text: str) -> str:
    """Merge standalone particles (pa, pi, in) to the preceding word.

    Zomi is tonal and spoken as separate syllables. Native speakers often
    write particles as standalone words. This merges them:
      "To pa" → "Topa"
      "Thang pi" → "Thangpi"
      "Thei in" → "Theiin"
    """
    lines = text.split("\n")
    merged = []
    for line in lines:
        if not line.strip():
            merged.append("")
            continue
        words = line.split()
        result = []
        i = 0
        while i < len(words):
            word = words[i]
            # Check if next word is a merge particle
            if i + 1 < len(words) and words[i + 1].lower() in MERGE_PARTICLES:
                # Only merge if the particle is short (2-3 chars)
                particle = words[i + 1]
                # But don't merge if the particle appears to be a full word
                # (e.g., "in" as preposition should sometimes stay separate)
                # We merge aggressively — user requested it
                result.append(word + particle)
                i += 2
            else:
                result.append(word)
                i += 1
        merged.append(" ".join(result))
    return "\n".join(merged)


PUNCTUATION = set(".,;:!?\"'()[]{}\u201c\u201d\u2018\u2019\u2032\u2033")


def _merge_next(text: str, target: str, label: str) -> str:
    """Merge standalone *target* after a word to that word (target merges LEFT).

      "paai ding" with target="ding" → "paaiding"
      "paai ding," → "paaiding,"
    """
    punc = PUNCTUATION
    lines = text.split("\n")
    merged = []
    for line in lines:
        if not line.strip():
            merged.append("")
            continue
        words = line.split()
        result = []
        i = 0
        while i < len(words):
            word = words[i]
            if i + 1 < len(words):
                nxt = words[i + 1]
                stripped = nxt.lower().rstrip("".join(punc))
                if stripped == target:
                    trail = nxt[len(nxt.rstrip("".join(punc))):]
                    result.append(word + target + trail)
                    i += 2
                    continue
            result.append(word)
            i += 1
        merged.append(" ".join(result))
    return "\n".join(merged)


def _merge_prev(text: str, target: str, label: str) -> str:
    """Merge standalone *target* before a word to that word (target merges RIGHT).

      "ki cing" with target="ki" → "kicing"
      "ki cing," → "kicing,"
    """
    punc = PUNCTUATION
    lines = text.split("\n")
    merged = []
    for line in lines:
        if not line.strip():
            merged.append("")
            continue
        words = line.split()
        result = []
        i = 0
        while i < len(words):
            word = words[i]
            stripped = word.lower().rstrip("".join(punc))
            trail = word[len(word.rstrip("".join(punc))):]
            if stripped == target and i + 1 < len(words):
                nxt = words[i + 1]
                result.append(target + nxt + trail)
                i += 2
                continue
            result.append(word)
            i += 1
        merged.append(" ".join(result))
    return "\n".join(merged)


def _merge_plural_te(text: str) -> str:
    """Merge standalone plural te to the preceding word."""
    return _merge_next(text, "te", "plural")


def _merge_agentive_n(text: str) -> str:
    """Merge agentive 'n suffix to the preceding word, keeping the apostrophe.

    The apostrophe is a visual separator that aids reading — do NOT remove it:
      "Topa'n" → "Topa'n"
      "Zeisu 'n" → "Zeisu'n"
      "te'n," → "te'n,"
    """
    text = text.replace("\u2019", "'")

    punctuation = PUNCTUATION

    lines = text.split("\n")
    merged = []
    for line in lines:
        if not line.strip():
            merged.append("")
            continue
        words = line.split()
        result = []
        i = 0
        while i < len(words):
            word = words[i]
            stripped = word.rstrip("".join(punctuation))
            trail = word[len(stripped):]

            if stripped.endswith("'n") and len(stripped) > 2:
                # Keep the apostrophe — it's a visual separator
                base = stripped[:-2]
                result.append(base + "'n" + trail)
            elif stripped.endswith("n") and i > 0 and stripped == "n" and result:
                result[-1] += "'n" + trail
            elif stripped == "'n":
                if result:
                    result[-1] += "'n" + trail
            else:
                result.append(word)
            i += 1
        merged.append(" ".join(result))
    return "\n".join(merged)


def _merge_prefix_ki(text: str) -> str:
    """Merge standalone prefix ki to the following word.

      "ki cing" → "kicing"
      "ki khawm" → "kikhawm"
      "ki sim" → "kisim"
    """
    return _merge_prev(text, "ki", "prefix-ki")


def _merge_suffix_cing(text: str) -> str:
    """Merge suffix cing to the preceding word for readability."""
    return _merge_next(text, "cing", "cing-suffix")


def _merge_suffix_gah(text: str) -> str:
    """Merge berry/hanging suffix gah to the preceding word."""
    return _merge_next(text, "gah", "gah-suffix")


def _merge_la(text: str) -> str:
    """Merge la (song) to the preceding word when it forms a compound.

      "thei la" → "Theila"
      "Zo la" → "Zola"
    """
    return _merge_next(text, "la", "song-la")


def _merge_ding(text: str) -> str:
    """Merge future/volitional ding to the preceding word.

      "paai ding" → "paaiding"
      "sem ding" → "semding"
    """
    return _merge_next(text, "ding", "future-ding")


def _merge_ta(text: str) -> str:
    """Merge perfective ta to the preceding word.

      "om ta" → "omta"
      "thei ta" → "theita"
    """
    return _merge_next(text, "ta", "perfective-ta")


def _merge_ah(text: str) -> str:
    """Merge locative ah to the preceding word.

      "khawm ah" → "khawmah"
      "inn ah" → "innah"
    """
    return _merge_next(text, "ah", "locative-ah")


def batch_normalize(input_path: Path, output_path: Path) -> dict:
    """Normalize an entire file and save. Returns stats."""
    if not input_path.exists():
        return {"input": str(input_path), "status": "not_found", "lines": 0}

    raw = input_path.read_text(encoding="utf-8", errors="ignore")
    original_lines = len([l for l in raw.split("\n") if l.strip()])

    normalized = normalize(raw)
    output_lines = len([l for l in normalized.split("\n") if l.strip()])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(normalized, encoding="utf-8")

    return {
        "input": str(input_path),
        "output": str(output_path),
        "original_lines": original_lines,
        "output_lines": output_lines,
        "removed": original_lines - output_lines,
    }
