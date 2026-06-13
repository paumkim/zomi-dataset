#!/usr/bin/env python3
"""
Zomi Community Submission Tool — accept Zomi text contributions from anyone.
Run as a web server to accept submissions, or use CLI to batch import.

Usage:
  python3 scripts/community_submit.py --serve    # Start web server
  python3 scripts/community_submit.py --import file.txt  # Import text file
"""

import json, os, sys, time, re, hashlib, html
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

BASE_DIR = Path(__file__).parent.parent
SUBMISSIONS_FILE = BASE_DIR / "data" / "community_submissions.jsonl"

# Zomi language markers (same as deep_discovery.py)
ZOMI_MARKERS = {
    "hi", "pen", "tawh", "ahi", "ci", "mite", "khempeuh",
    "ciangin", "bangin", "mahmah", "hiam", "hong", "om",
    "nawn", "kei", "Pasian", "Topa", "Laisiangtho", "Zeisu",
    "kammal", "thu", "pau", "gam", "sinna", "minam",
}

def is_zomi(text):
    if not text or len(text) < 20:
        return False
    words = set(text.lower().split())
    matches = words & ZOMI_MARKERS
    return len(matches) >= 2

def save_submission(data):
    data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    data["id"] = hashlib.md5((data["text"][:100] + str(time.time())).encode()).hexdigest()[:8]
    with open(SUBMISSIONS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")
    return data["id"]

def import_file(path):
    content = Path(path).read_text(encoding="utf-8", errors="ignore")
    lines = [l.strip() for l in content.split("\n") if l.strip()]
    count = 0
    for line in lines:
        if is_zomi(line):
            save_submission({
                "source": str(path),
                "text": line[:1000],
                "submitter": "batch_import",
            })
            count += 1
    print(f"Imported {count} Zomi lines from {path}")
    return count

# ─── Web Server ──────────────────────────────────────────────────────────

HTML_FORM = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pau — Submit Zomi Text</title>
<style>
  body{font-family:-apple-system,sans-serif;background:#0D1117;color:#E6EDF3;max-width:600px;margin:40px auto;padding:20px}
  h1{color:#D4A017}
  textarea{width:100%;padding:12px;background:#161B22;border:1px solid #30363D;color:#E6EDF3;border-radius:8px;font-size:14px;min-height:150px;font-family:inherit}
  input[type=text]{width:100%;padding:10px 12px;background:#161B22;border:1px solid #30363D;color:#E6EDF3;border-radius:8px;font-size:14px;margin:8px 0}
  button{background:#D4A017;color:#0D1117;border:none;padding:12px 24px;border-radius:8px;font-size:16px;font-weight:600;cursor:pointer}
  .note{color:#8B949E;font-size:13px;margin:12px 0}
  .success{color:#3FB950;margin:12px 0}
</style></head><body>
<h1>📝 Submit Zomi Text</h1>
<p>Help grow the Zomi dataset. Share Bible verses, song lyrics, news, or anything written in Zomi.</p>
<form method="POST">
  <label>Your Zomi text:</label>
  <textarea name="text" placeholder="Paste your Zomi text here..." required></textarea>
  <label>Source (optional):</label>
  <input type="text" name="source" placeholder="e.g., Zomi Daily, my church bulletin">
  <label>Your name (optional):</label>
  <input type="text" name="submitter" placeholder="e.g., John">
  <div class="note">By submitting, you agree this text can be used for Zomi AI training. No personal information will be stored.</div>
  <button type="submit">Submit</button>
</form>
</body></html>"""

HTML_SUCCESS = "<div class='success'>✅ Thank you! Your Zomi text has been saved.</div><p><a href='/' style='color:#D4A017'>Submit another →</a></p>"

class SubmitHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_FORM.encode())
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        params = {}
        for part in body.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                params[k] = urllib.parse.unquote_plus(v)
        text = params.get("text", "").strip()
        source = params.get("source", "").strip()
        submitter = params.get("submitter", "").strip()

        if text and is_zomi(text):
            sid = save_submission({"text": text[:1000], "source": source or "web_submission", "submitter": submitter or "anonymous"})
            response = HTML_SUCCESS + f"<p>Reference: {sid}</p>"
        else:
            response = "<div class='note'>⚠️ Could not detect Zomi text. Please make sure you're submitting Zomi (not English).</div>" + HTML_FORM

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(response.encode())

    def log_message(self, *a): pass

def serve():
    print("Community submission server at http://localhost:8766")
    HTTPServer(("0.0.0.0", 8766), SubmitHandler).serve_forever()

if __name__ == "__main__":
    import urllib.parse
    if "--serve" in sys.argv:
        serve()
    elif "--import" in sys.argv:
        idx = sys.argv.index("--import")
        import_file(sys.argv[idx + 1])
    else:
        print(__doc__)
