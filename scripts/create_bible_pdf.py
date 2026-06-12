"""
Create Tedim Bible PDF from verse text.
Output: Sinna/pdf/reference/tedim-laisiangtho-1932.pdf
"""

import os
from fpdf import FPDF


FONT_DIR = "/usr/share/fonts/TTF/"


class BiblePDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("DejaVu", "", os.path.join(FONT_DIR, "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf"))
        self.add_font("DejaVu", "I", os.path.join(FONT_DIR, "DejaVuSans-Oblique.ttf"))

    def header(self):
        if self.page_no() > 1:
            self.set_font("DejaVu", "I", 8)
            self.set_text_color(100, 100, 100)
            self.cell(0, 8, "Tedim Laisiangtho (1932)", align="C")
            self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"{self.page_no()}", align="C")

    def render(self, verses):
        self.set_auto_page_break(auto=True, margin=20)

        # Title page
        self.add_page()
        self.ln(60)
        self.set_font("DejaVu", "B", 28)
        self.set_text_color(139, 26, 26)
        self.cell(0, 15, "Tedim Laisiangtho", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)
        self.set_font("DejaVu", "", 16)
        self.set_text_color(80, 80, 80)
        self.cell(0, 12, "Tedim Bible (1932)", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(10)
        self.set_font("DejaVu", "I", 12)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"{len(verses):,} verses", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 10, "Zomi (Tedim/Zo) Language", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(15)
        self.set_font("DejaVu", "", 9)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, "github.com/paumkim/zomi-dataset", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 8, "paumkim.github.io/zomi-website", align="C", new_x="LMARGIN", new_y="NEXT")

        # Content
        self.add_page()
        self.set_font("DejaVu", "B", 16)
        self.set_text_color(139, 26, 26)
        self.cell(0, 12, "Tedim Laisiangtho", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

        para = []
        verse_count = 0
        for i, v in enumerate(verses, 1):
            para.append(f"({i}) {v}")
            verse_count += 1
            if verse_count % 25 == 0:
                self.set_font("DejaVu", "", 10)
                self.set_text_color(30, 30, 30)
                self.multi_cell(0, 5.5, " ".join(para))
                self.ln(3)
                para = []

        if para:
            self.set_font("DejaVu", "", 10)
            self.set_text_color(30, 30, 30)
            self.multi_cell(0, 5.5, " ".join(para))


def create_bible_pdf():
    base = os.path.dirname(os.path.dirname(__file__))
    output_dir = os.path.join(base, "Sinna", "pdf", "reference")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "tedim-laisiangtho-1932.pdf")

    verses_path = os.path.join(base, "data", "tedim1932_verses.txt")
    with open(verses_path, "r", encoding="utf-8") as f:
        verses = [line.strip() for line in f if line.strip()]

    pdf = BiblePDF()
    pdf.render(verses)
    pdf.output(output_path)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"PDF created: {output_path}")
    print(f"  Pages: {pdf.page_no()}")
    print(f"  Verses: {len(verses):,}")
    print(f"  Size: {size_mb:.1f} MB")
    return output_path


if __name__ == "__main__":
    create_bible_pdf()
