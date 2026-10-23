"""
Generates a PDF document for Capstone Checkpoint 1 Submission using PyMuPDF (fitz).
"""

import fitz
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DOC_PATH = BASE_DIR / "docs" / "submission_checkpoint_1.md"
PDF_PATH = BASE_DIR / "docs" / "ClaimSense_AI_Checkpoint_1_Submission.pdf"

def create_pdf():
    doc = fitz.open()
    
    # We will format the text onto standard Letter / A4 pages
    with open(DOC_PATH, "r") as f:
        text = f.read()

    # Create page 1
    page = doc.new_page(width=612, height=792) # Standard Letter
    margin_x = 50
    margin_y = 50
    rect = fitz.Rect(margin_x, margin_y, 612 - margin_x, 792 - margin_y)
    
    # Header
    page.insert_text((margin_x, margin_y + 15), "ClaimSense AI — Checkpoint 1 Submission", fontsize=16, fontname="helv", color=(0.1, 0.2, 0.4))
    page.insert_text((margin_x, margin_y + 35), "FDE Spine Capstone · Milestones 1 & 2 Checkpoint", fontsize=11, fontname="helv", color=(0.4, 0.4, 0.4))
    page.draw_line(fitz.Point(margin_x, margin_y + 45), fitz.Point(612 - margin_x, margin_y + 45), color=(0.2, 0.4, 0.8), width=1.5)

    y = margin_y + 65

    lines = text.splitlines()
    current_page = page
    
    for line in lines:
        if line.startswith("# "):
            continue # already handled in header
        elif line.startswith("## "):
            y += 10
            if y > 720:
                current_page = doc.new_page(width=612, height=792)
                y = margin_y + 20
            current_page.insert_text((margin_x, y), line.replace("## ", ""), fontsize=13, fontname="hebo", color=(0.15, 0.3, 0.6))
            y += 18
        elif line.startswith("### "):
            y += 6
            if y > 720:
                current_page = doc.new_page(width=612, height=792)
                y = margin_y + 20
            current_page.insert_text((margin_x, y), line.replace("### ", ""), fontsize=11, fontname="hebo", color=(0.2, 0.2, 0.2))
            y += 15
        elif line.startswith("```"):
            y += 4
        elif line.startswith("- [x] ") or line.startswith("* "):
            if y > 730:
                current_page = doc.new_page(width=612, height=792)
                y = margin_y + 20
            bullet_text = line.replace("- [x] ", "• [COMPLETED] ").replace("* ", "• ")
            # Wrap if long
            if len(bullet_text) > 85:
                part1 = bullet_text[:85]
                part2 = "    " + bullet_text[85:]
                current_page.insert_text((margin_x + 5, y), part1, fontsize=9, fontname="helv", color=(0.1, 0.1, 0.1))
                y += 12
                current_page.insert_text((margin_x + 5, y), part2, fontsize=9, fontname="helv", color=(0.1, 0.1, 0.1))
                y += 12
            else:
                current_page.insert_text((margin_x + 5, y), bullet_text, fontsize=9, fontname="helv", color=(0.1, 0.1, 0.1))
                y += 13
        elif line.strip() == "---":
            y += 8
            current_page.draw_line(fitz.Point(margin_x, y), fitz.Point(612 - margin_x, y), color=(0.8, 0.8, 0.8), width=0.5)
            y += 12
        elif line.strip():
            if y > 730:
                current_page = doc.new_page(width=612, height=792)
                y = margin_y + 20
            # Check for bold metadata
            current_page.insert_text((margin_x, y), line.replace("**", "").replace("*", ""), fontsize=9.5, fontname="helv", color=(0.2, 0.2, 0.2))
            y += 13
        else:
            y += 4

    # Add page numbers
    for i, p in enumerate(doc):
        p.insert_text((612 - margin_x - 60, 792 - margin_y + 10), f"Page {i+1} of {len(doc)}", fontsize=8, fontname="helv", color=(0.5, 0.5, 0.5))

    doc.save(str(PDF_PATH))
    print(f"✅ Generated submission PDF ({len(doc)} pages) at: {PDF_PATH}")

if __name__ == "__main__":
    create_pdf()
