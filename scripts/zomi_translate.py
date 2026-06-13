"""
Zomi Multi-Lingual Translator v2
Free translation using LibreTranslate + Zomi Tatoeba data.
Detects language, translates through English pivot, produces Zomi or target.

Usage:
  python3 scripts/zomi_translate.py "Apa khabar?"           → Zomi
  python3 scripts/zomi_translate.py "Ni hao ma?"            → Zomi
  python3 scripts/zomi_translate.py "Tuni na dam maw?" --to ms → Malay
  python3 scripts/zomi_translate.py --serve
"""

import json, sys, os, glob, re
from pathlib import Path
from translate import Translator as _Tr

BASE = Path(__file__).parent.parent
CACHE = Path.home() / ".cache" / "huggingface" / "hub"
TATOEBA = "datasets--ZomiLearner--English-Zomi-OPUS_Tatoeba_v20230412"

# ─── FREE TRANSLATOR (LibreTranslate) ─────────────────────────────────────

class FreeTranslate:
    """Free translation using translate library with retries."""
    
    def __call__(self, text, from_lang, to_lang):
        import time
        for attempt in range(3):
            try:
                t = _Tr(from_lang=from_lang, to_lang=to_lang)
                result = t.translate(text)
                if result and result != text:
                    return result
            except:
                time.sleep(2)
        return None


# ─── ZOMI TRANSLATOR (Tatoeba lookup) ─────────────────────────────────────

class ZomiTranslate:
    def __init__(self, max_pairs=50000):
        self.en_to_zomi = {}
        self.zomi_to_en = {}
        self._load(max_pairs)

    def _load(self, max_pairs):
        files = sorted(glob.glob(str(CACHE / TATOEBA / "snapshots" / "*" / "*.jsonl")))
        count = 0
        for f in files:
            with open(f) as fh:
                for line in fh:
                    d = json.loads(line)
                    en = d.get("en", "").strip()
                    zomi = d.get("zomi", "").strip()
                    if en and zomi and len(en) < 300:
                        key = en.lower()
                        if key not in self.en_to_zomi:
                            self.en_to_zomi[key] = zomi
                        key2 = zomi.lower()
                        if key2 not in self.zomi_to_en:
                            self.zomi_to_en[key2] = en
                        count += 1
                        if count >= max_pairs:
                            return

    def en_to_zo(self, text):
        key = text.lower().strip()
        if key in self.en_to_zomi:
            return self.en_to_zomi[key]
        # Word-by-word
        words = key.split()
        for i in range(len(words)):
            for j in range(i + 1, len(words) + 1):
                phrase = " ".join(words[i:j])
                if phrase in self.en_to_zomi:
                    return self.en_to_zomi[phrase]
        return None

    def zo_to_en(self, text):
        key = text.lower().strip()
        if key in self.zomi_to_en:
            return self.zomi_to_en[key]
        words = key.split()
        for i in range(len(words)):
            for j in range(i + 1, len(words) + 1):
                phrase = " ".join(words[i:j])
                if phrase in self.zomi_to_en:
                    return self.zomi_to_en[phrase]
        return None


# ─── LANGUAGE DETECTION ──────────────────────────────────────────────────

CHINESE_MARKERS = {"ni", "wo", "ta", "de", "shi", "zai", "bu", "le", "hen", "you", "hao",
                   "dao", "xia", "shang", "zhe", "na", "shenme", "ren", "jia", "tian",
                   "xihuan", "ai", "da", "xiao", "zhong", "guo", "ma", "la", "ba"}

MALAY_MARKERS = {"saya", "anda", "kita", "mereka", "dia", "ini", "itu", "dan", "atau",
                 "kerana", "sebab", "boleh", "mahu", "pergi", "ada", "tidak", "yang",
                 "untuk", "dengan", "pada", "ke", "di", "dari", "sudah", "akan", "lagi",
                 "apa", "khabar", "nama", "selamat", "terima", "kasih"}

ZOMI_MARKERS = {"hi", "pen", "in", "tawh", "leh", "mah", "zong", "Pasian", "Topa",
                "ciang", "bang", "mahmah", "hiam", "hong", "kei", "khempeuh", "zaw",
                "lo", "tampi", "mite", "ciangin", "bangin", "tua", "ahi"}

EN_MARKERS = {"the", "is", "are", "was", "were", "have", "has", "been", "will", "would",
              "could", "should", "this", "that", "these", "those", "i", "you", "he", "she",
              "we", "they", "my", "your", "his", "her", "its", "our", "their"}

def detect_lang(text):
    words = text.lower().split()
    scores = {
        "malay": sum(1 for w in words if w in MALAY_MARKERS),
        "chinese": sum(1 for w in words if w in CHINESE_MARKERS),
        "zomi": sum(1 for w in words if w in ZOMI_MARKERS),
        "english": sum(1 for w in words if w in EN_MARKERS),
    }
    best = max(scores, key=scores.get)
    # If English and another language tie, prefer the other language
    if scores[best] >= 1 and best != "english":
        return best
    if scores[best] >= 2:
        return best
    return "english"


# ─── MAIN PIPELINE ──────────────────────────────────────────────────────

def translate(text, target=None):
    if not text.strip():
        return ""

    ft = FreeTranslate()
    zo = ZomiTranslate()
    src = detect_lang(text)

    print(f"[Detected: {src}]", file=sys.stderr)

    # Language code mapping
    lang_codes = {"malay": "ms", "chinese": "zh", "english": "en", "zomi": "zom"}

    if target == "zomi" or (target is None and src != "zomi"):
        # Everything → Zomi
        if src == "zomi":
            return text
        if src == "english":
            result = zo.en_to_zo(text)
            if result:
                return result
            return f"(no Zomi match) {text}"

        # Malay/Chinese → English → Zomi
        en = ft(text, lang_codes.get(src, "ms"), "en")
        if en:
            result = zo.en_to_zo(en)
            if result:
                return result
            return f"(no Zomi match for) {en}"
        return f"Could not translate from {src}"

    elif target in ("malay", "ms", "chinese", "zh", "english", "en"):
        # Zomi → target
        if src != "zomi":
            return "Input doesn't look like Zomi."

        en = zo.zo_to_en(text)
        if not en:
            return "(no English match for this Zomi text)"

        if target in ("english", "en"):
            return en

        tc = lang_codes.get(target, "ms")
        result = ft(en, "en", tc)
        return result or f"(no translation) {en}"

    else:
        # Auto: detect target based on source
        if src == "zomi":
            # Zomi → English by default
            en = zo.zo_to_en(text)
            return en or "(no English match)"
        else:
            # Everything → Zomi
            return translate(text, "zomi")


def main():
    import sys

    if "--serve" in sys.argv:
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import urllib.parse

        HTML = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Zomi Multi-Translator</title>
<style>
body{font-family:sans-serif;max-width:700px;margin:40px auto;padding:20px;background:#0D1117;color:#E6EDF3;font-size:16px}
textarea{width:calc(100% - 24px);padding:10px;background:#161B22;border:1px solid #30363D;color:#E6EDF3;border-radius:6px;font-size:16px;min-height:80px}
select,button{padding:10px 18px;background:#161B22;border:1px solid #30363D;color:#E6EDF3;border-radius:6px;font-size:14px;cursor:pointer}
button{background:#D4A017;color:#0D1117;border:none;font-weight:600;margin:8px 4px}
.result{padding:20px;background:#161B22;border-radius:8px;margin:12px 0;font-size:18px;line-height:1.6}
.note{color:#8B949E;font-size:13px}
</style></head><body>
<h1>🌐 Zomi Translator</h1>
<p style="color:#8B949E;">Malay → Zomi · Chinese → Zomi · English → Zomi · Zomi → Malay/Chinese/English</p>
<form method="POST">
<select name="target">
<option value="">Auto detect</option>
<option value="zomi">→ Zomi</option>
<option value="ms">→ Malay</option>
<option value="zh">→ Chinese</option>
<option value="en">→ English</option>
</select>
<textarea name="text" placeholder="Enter text...">{INPUT}</textarea>
<br><button type="submit">Translate</button>
</form>
<div class="result">{RESULT}</div>
<div class="note">Powered by LibreTranslate + Zomi Tatoeba dataset.</div>
</body></html>"""

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_html(HTML.replace("{INPUT}","").replace("{RESULT}","Enter text."))
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode() if length else ""
                params = dict(p.split("=", 1) for p in body.split("&") if "=" in p)
                text = urllib.parse.unquote_plus(params.get("text", ""))
                target = params.get("target", "")
                result = translate(text, target) if text else ""
                self.send_html(HTML.replace("{INPUT}",text).replace("{RESULT}",result))
            def send_html(self, h):
                self.send_response(200)
                self.send_header("Content-Type","text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(h.encode())
            def log_message(self,*a): pass

        print("Server at http://localhost:8765", file=sys.stderr)
        HTTPServer(("0.0.0.0", 8765), Handler).serve_forever()

    else:
        text = " ".join(a for a in sys.argv[1:] if not a.startswith("--"))
        target = None
        for i, a in enumerate(sys.argv):
            if a == "--to" and i + 1 < len(sys.argv):
                target = sys.argv[i + 1]

        if text:
            result = translate(text, target)
            print(result)
        else:
            print(__doc__)

if __name__ == "__main__":
    main()
