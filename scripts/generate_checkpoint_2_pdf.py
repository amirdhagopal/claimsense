"""
Generates a PDF document for Capstone Checkpoint 2 (Final) Submission using PyMuPDF (fitz).
"""

import fitz
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DOC_PATH = BASE_DIR / "docs" / "submission_checkpoint_2.md"
PDF_PATH = BASE_DIR / "docs" / "ClaimSense_AI_Checkpoint_2_Final_Submission.pdf"

def create_pdf():
    doc = fitz.open()
    
    with open(DOC_PATH, "r") as f:
        text = f.read()

    # Create page 1
    page = doc.new_page(width=612, height=792) # Standard Letter
    margin_x = 50
    margin_y = 50
    
    # Header
    page.insert_text((margin_x, margin_y + 15), "ClaimSense AI — Checkpoint 2 Final Submission", fontsize=16, fontname="hebo", color=(0.1, 0.2, 0.45))
    page.insert_text((margin_x, margin_y + 35), "FDE Spine Capstone · Final Deliverable (Milestones 1–5)", fontsize=11, fontname="helv", color=(0.4, 0.4, 0.4))
    page.draw_line(fitz.Point(margin_x, margin_y + 45), fitz.Point(612 - margin_x, margin_y + 45), color=(0.2, 0.4, 0.8), width=1.5)

    y = margin_y + 65

    lines = text.splitlines()
    current_page = page
    
    for line in lines:
        if line.startswith("# "):
            continue
        elif line.startswith("## "):
            y += 12
            if y > 720:
                current_page = doc.new_page(width=612, height=792)
                y = margin_y + 20
            current_page.insert_text((margin_x, y), line.replace("## ", ""), fontsize=12.5, fontname="hebo", color=(0.12, 0.28, 0.55))
            y += 18
        elif line.startswith("### "):
            y += 8
            if y > 720:
                current_page = doc.new_page(width=612, height=792)
                y = margin_y + 20
            current_page.insert_text((margin_x, y), line.replace("### ", ""), fontsize=10.5, fontname="hebo", color=(0.2, 0.2, 0.2))
            y += 15
        elif line.startswith("|") and "---" in line:
            continue
        elif line.startswith("|"):
            if y > 730:
                current_page = doc.new_page(width=612, height=792)
                y = margin_y + 20
            cols = [c.strip() for c in line.split("|")[1:-1]]
            row_str = "  |  ".join(cols)
            if len(row_str) > 90:
                row_str = row_str[:88] + "..."
            current_page.insert_text((margin_x, y), row_str, fontsize=8.5, fontname="helv", color=(0.15, 0.15, 0.15))
            y += 12
        elif line.startswith("* ") or line.startswith("- "):
            if y > 730:
                current_page = doc.new_page(width=612, height=792)
                y = margin_y + 20
            bullet_text = "• " + line[2:].replace("**", "").replace("*", "")
            if len(bullet_text) > 85:
                part1 = bullet_text[:85]
                part2 = "    " + bullet_text[85:]
                current_page.insert_text((margin_x + 5, y), part1, fontsize=9, fontname="helv", color=(0.15, 0.15, 0.15))
                y += 12
                current_page.insert_text((margin_x + 5, y), part2, fontsize=9, fontname="helv", color=(0.15, 0.15, 0.15))
                y += 12
            else:
                current_page.insert_text((margin_x + 5, y), bullet_text, fontsize=9, fontname="helv", color=(0.15, 0.15, 0.15))
                y += 13
        elif line.strip() == "---":
            y += 6
            current_page.draw_line(fitz.Point(margin_x, y), fitz.Point(612 - margin_x, y), color=(0.8, 0.8, 0.8), width=0.5)
            y += 10
        elif line.strip():
            if y > 730:
                current_page = doc.new_page(width=612, height=792)
                y = margin_y + 20
            clean_line = line.replace("**", "").replace("*", "")
            if len(clean_line) > 85:
                part1 = clean_line[:85]
                part2 = "  " + clean_line[85:]
                current_page.insert_text((margin_x, y), part1, fontsize=9, fontname="helv", color=(0.2, 0.2, 0.2))
                y += 12
                current_page.insert_text((margin_x, y), part2, fontsize=9, fontname="helv", color=(0.2, 0.2, 0.2))
                y += 12
            else:
                current_page.insert_text((margin_x, y), clean_line, fontsize=9, fontname="helv", color=(0.2, 0.2, 0.2))
                y += 13
        else:
            y += 4

    # Add page numbers and footer
    for i, p in enumerate(doc):
        p.draw_line(fitz.Point(margin_x, 792 - margin_y), fitz.Point(612 - margin_x, 792 - margin_y), color=(0.85, 0.85, 0.85), width=0.5)
        p.insert_text((margin_x, 792 - margin_y + 12), "ClaimSense AI — Forward Deployed Engineering Capstone", fontsize=8, fontname="helv", color=(0.5, 0.5, 0.5))
        p.insert_text((612 - margin_x - 65, 792 - margin_y + 12), f"Page {i+1} of {len(doc)}", fontsize=8, fontname="helv", color=(0.5, 0.5, 0.5))

    doc.save(str(PDF_PATH))
    print(f"✅ Generated Checkpoint 2 PDF ({len(doc)} pages) at: {PDF_PATH}")

if __name__ == "__main__":
    create_pdf()
