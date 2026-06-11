import subprocess
import re
import html

URLS = [
    "/",
    "/staff",
    "/ministries",
    "/our_beliefs",
    "/salvation",
    "/prayer",
    "/links",
    "/map_directions",
    "/hau_pian_cing",
    "/muana_khuptong",
    "/cleaning",
    "/musicians_te",
    "/choir_ministry",
    "/decor_department_paksuan",
    "/cook_ann_huan_department",
    "/chairman",
    "/secretary",
    "/vice_chairman",
    "/assistant_secretary",
    "/trustee",
    "/trustee_6905",
    "/trustee_6907",
    "/ob_member_mission_director",
    "/wm_women_ministry_department",
    "/av_audio_and_visual_media_media_worship_and_choir__department",
    "/mission_department",
    "/building_committee",
    "/youth_ministry",
    "/ushers",
    "/sunday_school_children_ministry",
]

def fetch_html(path):
    url = f"http://zomibethelchurch.org{path}"
    try:
        result = subprocess.run(["curl", "-s", "-L", url], capture_output=True, text=True, timeout=30)
        return result.stdout
    except Exception as e:
        return ""

def extract_inner_content(html_text):
    match = re.search(r'<div class="innerContent"[^>]*>(.*?)</div>\s*<!-- end \.innerContent -->', html_text, re.DOTALL)
    if not match:
        match = re.search(r'<div class="innerContent"[^>]*>(.*?)</div>', html_text, re.DOTALL)
    if match:
        content = match.group(1)
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
        content = re.sub(r'<[^>]+>', ' ', content)
        content = html.unescape(content)
        content = re.sub(r'&nbsp;', ' ', content)
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()
        return content if len(content) > 50 else ""
    return ""

all_pages = {}
home_content = ""

for path in URLS:
    html_text = fetch_html(path)
    text = extract_inner_content(html_text)
    
    title_match = re.search(r'<title>(.*?)</title>', html_text, re.DOTALL)
    title = title_match.group(1).strip() if title_match else path
    
    if path == "/":
        home_content = text
    
    if text and len(text) > 50:
        if text == home_content and path != "/":
            print(f"SKIP (same as home): {path}")
            continue
        all_pages[path] = (title, text)
        print(f"OK: {path} ({len(text)} chars)")
    else:
        print(f"EMPTY: {path}")

lines = []
for path in URLS:
    if path in all_pages:
        title, text = all_pages[path]
        lines.append(f"=== PAGE: {path} ===")
        lines.append(text)
        lines.append("")

output = "\n".join(lines)
with open("/home/pauk/zomi_dataset/data/zomibethelchurch_raw.txt", "w", encoding="utf-8") as f:
    f.write(output)

total_chars = len(output)
print(f"\nTotal pages: {len(all_pages)}")
print(f"Total characters: {total_chars}")
