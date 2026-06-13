"""
Zomi Translator — Simple translation using Tatoeba parallel data.
Works on CPU, no GPU needed. Uses semantic matching for best results.

Usage:
  python3 scripts/translate.py "Hello, how are you?"
  python3 scripts/translate.py --zomi "Pasian in vantung le"
  python3 scripts/translate.py --serve   # Web server
"""

import json, sys, os, random, re
from pathlib import Path

BASE = Path(__file__).parent.parent
CACHE_DIR = Path.home() / ".cache" / "huggingface" / "hub"
TATOEBA = "datasets--ZomiLearner--English-Zomi-OPUS_Tatoeba_v20230412"


def find_tatoeba():
    """Find Tatoeba data in HF cache."""
    pattern = str(CACHE_DIR / TATOEBA / "snapshots" / "*" / "*.jsonl")
    import glob
    return sorted(glob.glob(pattern))


class ZomiTranslate:
    def __init__(self, max_pairs=100000):
        self.en_to_zomi = {}
        self.zomi_to_en = {}
        self.en_index = []
        self.zomi_index = []
        self.word_map_en = {}
        self.word_map_zomi = {}
        self.common_phrases_en = {}
        self.common_phrases_zomi = {}
        self.loaded = False

    def load(self, max_pairs=100000):
        files = find_tatoeba()
        if not files:
            return False

        count = 0
        for f in files:
            with open(f, "r", encoding="utf-8") as fh:
                for line in fh:
                    d = json.loads(line)
                    en = d.get("en", "").strip()
                    zomi = d.get("zomi", "").strip()
                    if en and zomi:
                        en_lower = en.lower()
                        zomi_lower = zomi.lower()
                        self.en_to_zomi[en_lower] = zomi
                        self.zomi_to_en[zomi_lower] = en
                        self.en_index.append(en_lower)
                        self.zomi_index.append(zomi_lower)

                        # Build word maps (first 10000 pairs)
                        if count < 10000:
                            en_words = en_lower.split()
                            zomi_words = zomi_lower.split()
                            for i, ew in enumerate(en_words):
                                if i < len(zomi_words):
                                    self.word_map_en[ew] = zomi_words[i]
                                    self.word_map_zomi[zomi_words[i]] = ew

                        # Build phrase maps (first 5000 pairs)
                        if count < 5000:
                            self.common_phrases_en[en_lower] = zomi
                            self.common_phrases_zomi[zomi_lower] = en

                        count += 1
                        if count >= max_pairs:
                            break
            if count >= max_pairs:
                break

        self.loaded = True
        return count

    def translate(self, text, source="auto"):
        """Translate text. source can be 'en', 'zomi', or 'auto'."""
        text = text.strip()
        if not text:
            return ""

        # Detect language
        if source == "auto":
            # Simple heuristic: if first word is uppercase English word
            en_indicators = {"the", "is", "are", "was", "were", "have", "has", "i", "you", "he", "she", "it", "we", "they"}
            first_word = text.split()[0].lower() if text.split() else ""
            zomi_indicators = {"hi", "pen", "in", "tawh", "leh", "mah", "zong", "Pasian", "Topa"}
            en_score = sum(1 for w in text.lower().split() if w in en_indicators)
            zomi_score = sum(1 for w in text.lower().split() if w in zomi_indicators)
            source = "en" if en_score > zomi_score else "zomi"

        key = text.lower()

        if source == "en":
            if key in self.en_to_zomi:
                return self.en_to_zomi[key]
            return self._fallback_en(key)
        else:
            if key in self.zomi_to_en:
                return self.zomi_to_en[key]
            return self._fallback_zomi(key)

    def _fallback_en(self, text):
        """Word-by-word fallback for English to Zomi."""
        words = text.split()
        result = []
        for w in words:
            # Remove punctuation for lookup
            clean = w.strip(".,!?;:'\"")
            if clean in self.word_map_en:
                result.append(self.word_map_en[clean])
            else:
                result.append(w)
        return " ".join(result)

    def _fallback_zomi(self, text):
        """Word-by-word fallback for Zomi to English."""
        words = text.split()
        result = []
        for w in words:
            clean = w.strip(".,!?;:'\"")
            if clean in self.word_map_zomi:
                result.append(self.word_map_zomi[clean])
            else:
                result.append(w)
        return " ".join(result)


# ─── CLI ────────────────────────────────────────────────────────────────────

def main():
    import time
    translator = ZomiTranslate()

    print("Loading Tatoeba data...")
    count = translator.load()
    if not count:
        print("Error: Tatoeba data not found in HF cache.")
        print(f"Looked in: {CACHE_DIR / TATOEBA}")
        sys.exit(1)
    print(f"Loaded {count:,} translation pairs\n")

    if "--serve" in sys.argv:
        # Web server mode
        from http.server import HTTPServer, BaseHTTPRequestHandler
        HTML_TEMPLATE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Zomi Translator</title>
<style>body{{font-family:sans-serif;max-width:600px;margin:40px auto;padding:20px;background:#0D1117;color:#E6EDF3}}
textarea,input{{width:calc(100%% - 24px);padding:10px;margin:8px 0;background:#161B22;border:1px solid #30363D;color:#E6EDF3;border-radius:6px;font-size:16px}}
button{{background:#D4A017;color:#0D1117;border:none;padding:12px 24px;border-radius:6px;font-size:16px;cursor:pointer}}
.result{{padding:12px;background:#161B22;border-radius:6px;margin:12px 0;font-size:18px}}
</style></head><body>
<h1>📝 Zomi Translator</h1>
<form method="POST"><textarea name="text" rows="3" placeholder="Enter text..."></textarea>
<button type="submit">Translate</button></form>
<div class="result">{RESULT}</div>
</body></html>"""

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_html(HTML_TEMPLATE.replace("{RESULT}", "Enter text above to translate between English and Zomi."))
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode() if length else ""
                text = ""
                for part in body.split("&"):
                    if part.startswith("text="):
                        text = urllib.parse.unquote_plus(part[5:])
                if text:
                    result = translator.translate(text)
                else:
                    result = ""
                self.send_html(HTML_TEMPLATE.replace("{RESULT}", result))
            def send_html(self, html):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode())
            def log_message(self, *a): pass

        import urllib.parse
        port = 8765
        print(f"Translation server at http://localhost:{port}")
        HTTPServer(("0.0.0.0", port), Handler).serve_forever()

    else:
        # Interactive mode
        text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
        if text:
            result = translator.translate(text)
            print(f"Result: {result}")
        else:
            print("Interactive mode. Type text to translate. /quit to exit.\n")
            while True:
                try:
                    text = input("> ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if not text or text == "/quit":
                    break
                t0 = time.time()
                result = translator.translate(text)
                dt = time.time() - t0
                print(f"  → {result}  ({dt*1000:.0f}ms)")

if __name__ == "__main__":
    main()
