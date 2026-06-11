"""
Extract song metadata (Key, BPM, TimeSig, chord PDFs, YouTube) for ALL 176 songs.
Uses the same real browser + navigation pattern as the lyrics collector.
Navigate via the main page to avoid individual Cloudflare challenges.
"""
import json, re, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from crawl.lyrics_collector import launch_real_browser, LYRICS_URL

songs = json.loads((Path(__file__).parent.parent / "crawl" / "lyrics_progress.json").read_text()).get("songs", [])
print(f"Songs: {len(songs)}", flush=True)

out = Path.home() / "zomi_dataset" / "data" / "worship_metadata"
out.mkdir(parents=True, exist_ok=True)
chord_dir = out / "chord_pdfs"
chord_dir.mkdir(exist_ok=True)

browser, playwright, chrome_process = launch_real_browser()

# Go to the main lyrics page first (establishes session)
page = browser.new_page()
print("Navigating to main lyrics page...", flush=True)
page.goto(LYRICS_URL, timeout=30000, wait_until="domcontentloaded")
time.sleep(3)

all_meta = []

for i, song in enumerate(songs):
    url = song.get("url", "")
    title = song.get("title", "unknown").strip()[:40]
    artist = song.get("artist", "unknown").strip()[:20]
    if not url: continue
    
    meta = {"title": song.get("title","").strip(), "artist": song.get("artist","").strip(), "url": url}
    
    try:
        page.goto(url, timeout=15000, wait_until="domcontentloaded")
        time.sleep(2)
        
        # Get page text — this is what the lyrics collector used successfully
        text = page.inner_text("body")
        
        # Extract key/BPM/timesig from the text
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith("Key:"): meta["key"] = line.replace("Key:", "").strip()
            if line.startswith("BPM:"): meta["bpm"] = line.replace("BPM:", "").strip()
            if line.startswith("TimeSig:"): meta["timesig"] = line.replace("TimeSig:", "").strip()
        
        # Try to find chord PDF links from the page
        html = page.content()
        pdfs = re.findall(r'href="([^"]*\.pdf)"', html)
        chord_pdfs = []
        for pdf_url in pdfs:
            if "Lyrics" not in pdf_url and "lyrics" not in pdf_url.lower():
                mk = re.search(r'[\/-]([A-G][#b]?)(?=\.pdf)', pdf_url)
                label = mk.group(1) if mk else pdf_url.split("/")[-1]
                chord_pdfs.append({"url": pdf_url, "key": label})
        if chord_pdfs:
            meta["chord_pdfs"] = chord_pdfs
            # Download a couple as proof
            for cp in chord_pdfs[:2]:
                try:
                    resp = page.goto(cp["url"], timeout=10000)
                    if resp and resp.status == 200:
                        d = resp.body()
                        if len(d) > 1000:
                            fn = cp["url"].split("/")[-1].split("?")[0]
                            fp = chord_dir / fn
                            if not fp.exists():
                                fp.write_bytes(d)
                except: pass
        
        # Find YouTube
        ym = re.search(r'href="([^"]*youtube[^"]+)"', html) or re.search(r'src="([^"]*youtube[^"]+)"', html)
        if ym: meta["youtube"] = ym.group(1)
        
        all_meta.append(meta)
        k = meta.get("key", "?")
        print(f"  [{i+1}] {artist:20s} {title:40s} K:{k}", flush=True)
        
    except Exception as e:
        print(f"  [X] {title:40s} {str(e)[:50]}", flush=True)
    
    time.sleep(0.3)

# Save
outf = out / "song_metadata.json"
outf.write_text(json.dumps(all_meta, indent=2, ensure_ascii=False))
pdfs = len(list(chord_dir.glob("*.pdf")))
keys = sum(1 for m in all_meta if m.get("key"))
print(f"\nDone! {len(all_meta)} songs, {keys} with keys, {pdfs} chord PDFs", flush=True)

browser.close()
playwright.stop()
chrome_process.kill()
