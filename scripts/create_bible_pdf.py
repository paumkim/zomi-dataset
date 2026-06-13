"""
Create Tedim Bible PDF — traditional two-column Bible layout.
Like a printed Bible: compact verses, columns, verse numbers.
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
        self.col = 0        # current column (0-left, 1-right)
        self.col_w = 80     # column width
        self.col_gap = 10   # gap between columns
        self.margin = 12    # left/right margin
        self.y0 = 25        # starting y position
        self.page_height = 285
        self.line_h = 4.2   # line height for verse text

    def header(self):
        if self.page_no() > 1:
            self.set_font("DejaVu", "I", 7)
            self.set_text_color(80, 80, 80)
            self.cell(0, 6, "Tedim Laisiangtho (1932)", align="C")
            self.ln(8)

    def footer(self):
        self.set_y(-12)
        self.set_font("DejaVu", "I", 7)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"— {self.page_no()} —", align="C")

    def col_start(self):
        x = self.margin + self.col * (self.col_w + self.col_gap)
        self.set_xy(x, self.y0)

    def col_next(self):
        self.col = 1 - self.col
        if self.col == 0:
            self.add_page()
            self.col = 0
        self.col_start()

    def render_verses(self, verses, chunk_size=15):
        self.set_auto_page_break(auto=True, margin=20)
        self.col = 0
        self.col_start()
        self.set_font("DejaVu", "", 7.5)
        self.set_text_color(20, 20, 20)

        for i, v in enumerate(verses, 1):
            text = f"\xb6{i} {v} "
            # Check if we need a new column or page
            x = self.margin + self.col * (self.col_w + self.col_gap)
            self.set_xy(x, self.get_y())

            # Write the verse text
            self.multi_cell(self.col_w, self.line_h, text)

            # Check if we need to move to next column
            if self.get_y() > self.page_height - 25:
                self.col_next()

        # Fill remaining space on last page
        self.ln(5)

    def render(self, verses):
        self.set_auto_page_break(auto=True, margin=20)

        # ── Title Page ──
        self.add_page()
        self.ln(50)
        self.set_font("DejaVu", "B", 26)
        self.set_text_color(120, 20, 20)
        self.cell(0, 14, "Tedim Laisiangtho", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        self.set_font("DejaVu", "", 14)
        self.set_text_color(80, 80, 80)
        self.cell(0, 10, "Tedim Bible (1932)", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(8)
        self.set_font("DejaVu", "I", 10)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"{len(verses):,} verses in Zomi (Tedim/Zo)", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(140, 140, 140)
        self.cell(0, 6, "github.com/paumkim/zomi-dataset", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 6, "paumkim.github.io/zomi-website", align="C", new_x="LMARGIN", new_y="NEXT")

        # ── Bible Content ──
        self.add_page()
        self.set_font("DejaVu", "B", 14)
        self.set_text_color(120, 20, 20)
        self.cell(0, 10, "Tedim Laisiangtho", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        self.set_font("DejaVu", "I", 7.5)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, "Pasian' Kammal — Lai Siangtho (1932)", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

        self.col = 0
        self.col_start()
        self.render_verses(verses)


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
