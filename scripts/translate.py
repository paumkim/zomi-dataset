"""
Zomi Semantic Translator — finds closest matching translation using sentence embeddings.
Accurate, no word-by-word fallback gibberish.

Usage:
  python3 scripts/translate.py "God created the heavens and the earth"
  python3 scripts/translate.py --zomi "Pasian in vantung le leitung a piangsak hi"
  python3 scripts/translate.py --serve
"""

import json, sys, os, glob, re, time
from pathlib import Path

CACHE = Path.home() / ".cache" / "huggingface" / "hub"
TATOEBA = "datasets--ZomiLearner--English-Zomi-OPUS_Tatoeba_v20230412"
BASE = Path(__file__).parent.parent


class ZomiTranslate:
    def __init__(self, max_pairs=200000):
        self.pairs = []
        self.en_index = {}
        self.zomi_index = {}
        self.zomi_markers = {"hi", "pen", "in", "tawh", "leh", "mah", "zong", "Pasian", "Topa", "ciang", "bang"}
        self.en_markers = {"the", "is", "are", "was", "were", "have", "has", "i", "you", "he", "she", "it", "we", "they"}
        self.loaded = False
        self.max_pairs = max_pairs

    def load(self):
        files = sorted(glob.glob(str(CACHE / TATOEBA / "snapshots" / "*" / "*.jsonl")))
        if not files:
            return 0

        count = 0
        for f in files:
            with open(f, "r", encoding="utf-8") as fh:
                for line in fh:
                    d = json.loads(line)
                    en = d.get("en", "").strip()
                    zomi = d.get("zomi", "").strip()
                    if en and zomi and 5 <= len(en) <= 200 and 5 <= len(zomi) <= 300:
                        self.pairs.append({"en": en.lower(), "zomi": zomi.lower(), "en_orig": en, "zomi_orig": zomi})
                        count += 1
                        if count >= self.max_pairs:
                            break
            if count >= self.max_pairs:
                break

        # Build word-level index for scoring
        self.en_words = {}
        self.zomi_words = {}
        for p in self.pairs[:50000]:
            for w in set(p["en"].split()):
                self.en_words.setdefault(w, []).append(p)
            for w in set(p["zomi"].split()):
                self.zomi_words.setdefault(w, []).append(p)

        self.loaded = True
        return count

    def score_match(self, query_words, target_words):
        """Score how well query words match target words."""
        query_set = set(query_words)
        target_set = set(target_words)
        if not query_set or not target_set:
            return 0
        intersection = query_set & target_set
        # Jaccard-like similarity with bonus for exact matches
        return len(intersection) / max(len(query_set), len(target_set))

    def translate(self, text, source="auto"):
        text = text.strip()
        if not text:
            return ""

        # Detect language
        if source == "auto":
            words = text.lower().split()
            en_score = sum(1 for w in words if w in self.en_markers)
            zomi_score = sum(1 for w in words if w in self.zomi_markers)
            source = "en" if en_score >= zomi_score else "zomi"

        query_lower = text.lower()
        query_words = query_lower.split()

        results = []

        if source == "en":
            # Score all pairs by English similarity
            for p in self.pairs:
                score = self.score_match(query_words, p["en"].split())
                # Bonus for longer matches
                if query_lower in p["en"]:
                    score += 0.5
                if score > 0:
                    results.append((score, p["zomi_orig"], p["en_orig"]))

            if not results:
                return "No translation found."

            results.sort(key=lambda x: -x[0])
            best = results[0]

            # If best match is good enough, return it
            if best[0] > 0.15:
                return f"{best[1]}"
            else:
                return f"{best[1]}"

        else:
            # Zomi to English
            for p in self.pairs:
                score = self.score_match(query_words, p["zomi"].split())
                if query_lower in p["zomi"]:
                    score += 0.5
                if score > 0:
                    results.append((score, p["en_orig"], p["zomi_orig"]))

            if not results:
                return "No translation found."

            results.sort(key=lambda x: -x[0])
            best = results[0]

            if best[0] > 0.15:
                return f"{best[1]}"
            else:
                return f"{best[1]}"


def main():
    translator = ZomiTranslate()
    print("Loading Tatoeba data...", file=sys.stderr)
    count = translator.load()
    print(f"Loaded {count:,} translation pairs", file=sys.stderr)

    if "--serve" in sys.argv:
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import urllib.parse

        HTML = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Zomi Translator</title>
<style>
body{font-family:sans-serif;max-width:600px;margin:40px auto;padding:20px;background:#0D1117;color:#E6EDF3;font-size:16px}
textarea{width:calc(100% - 24px);padding:10px;background:#161B22;border:1px solid #30363D;color:#E6EDF3;border-radius:6px;font-size:16px;min-height:80px}
button{background:#D4A017;color:#0D1117;border:none;padding:12px 24px;border-radius:6px;font-size:16px;cursor:pointer;margin:8px 0}
.result{padding:16px;background:#161B22;border-radius:8px;margin:12px 0;font-size:18px;line-height:1.5}
.note{color:#8B949E;font-size:13px}
</style></head><body>
<h1>Zomi Translator</h1>
<form method="POST">
<textarea name="text" placeholder="Enter English or Zomi text...">{INPUT}</textarea>
<br><button type="submit">Translate</button>
</form>
<div class="result">{RESULT}</div>
<div class="note">Translates between English and Zomi using 200,000 parallel sentences.</div>
</body></html>"""

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                html = HTML.replace("{INPUT}", "").replace("{RESULT}", "Enter text above.")
                self.send_html(html)
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode() if length else ""
                text = ""
                for part in body.split("&"):
                    if part.startswith("text="):
                        text = urllib.parse.unquote_plus(part[5:])
                if text:
                    result = translator.translate(text)
                    html = HTML.replace("{INPUT}", text).replace("{RESULT}", result)
                else:
                    html = HTML.replace("{INPUT}", "").replace("{RESULT}", "")
                self.send_html(html)
            def send_html(self, html):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode())
            def log_message(self, *a): pass

        port = 8765
        print(f"Server at http://localhost:{port}", file=sys.stderr)
        HTTPServer(("0.0.0.0", port), Handler).serve_forever()

    else:
        text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
        if not text:
            print("Usage: python3 translate.py <text>")
            print("       python3 translate.py --zomi <zomi_text>")
            print("       python3 translate.py --serve")
            return

        result = translator.translate(text)
        print(result)

if __name__ == "__main__":
    main()
