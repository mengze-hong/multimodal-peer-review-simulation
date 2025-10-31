# pdf_utilities.py
import fitz  # PyMuPDF
import tempfile
import os
import re
import shutil
from PyPDF2 import PdfReader
from PIL import Image
from openai import OpenAI
import httpx, json
import streamlit as st

# ====================================================
# PDF Extraction Utilities
# ====================================================
def extract_full_text(pdf_path: str) -> str:
    """Extract all text from a PDF file."""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text.strip()

def extract_title_and_abstract(text: str):
    """Heuristically extract a likely title and the abstract from scientific text."""
    # Clean and split
    text = text.strip()
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    # --- 🎯 TITLE DETECTION ---
    title = "Untitled"
    for line in paragraphs[:5]:  # only check first few lines
        # Skip lines that look like metadata or sections
        if re.match(r"^(abstract|introduction|authors?|submitted|doi|copyright|keywords?)", line, re.I):
            continue
        if re.match(r"^\d+[\.\)]?\s+", line):  # numbered headings
            continue
        if len(line.split()) < 3:  # too short
            continue
        if len(line) > 200:  # too long to be a title
            continue
        # Found a plausible title
        title = line.strip()
        break

    # --- 🧩 ABSTRACT DETECTION ---
    pattern = r"(?:^|\n)(?:Abstract|ABSTRACT)\s*[:\-]?\s*(.*?)(?=\n[A-Z][A-Za-z ]{2,}|$)"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        abstract = match.group(1).strip()
    else:
        # Fall back to a few paragraphs after the title
        idx = paragraphs.index(title) if title in paragraphs else 0
        abstract_candidates = paragraphs[idx+1 : idx+6]
        abstract = " ".join(abstract_candidates)[:1200]

    return title, abstract



def merge_images_grid(image_paths, cols: int = 2, bg_color=(255, 255, 255)) -> str:
    """Merge individual page images into a single grid preview PNG."""
    images = [Image.open(p) for p in image_paths]
    w, h = max(im.width for im in images), max(im.height for im in images)
    rows = (len(images) + cols - 1) // cols

    grid = Image.new("RGB", (cols * w, rows * h), color=bg_color)
    for idx, im in enumerate(images):
        r, c = divmod(idx, cols)
        grid.paste(im, (c * w, r * h))

    temp_fd, temp_img_path = tempfile.mkstemp(suffix=".png")
    grid.save(temp_img_path)
    os.close(temp_fd)
    return temp_img_path


def extract_and_merge_images(pdf_path: str, dpi: int = 150) -> str:
    """Render all PDF pages to images and merge into one temporary PNG preview."""
    temp_dir = tempfile.mkdtemp(prefix="pdf_pages_")
    doc = fitz.open(pdf_path)
    image_paths = []

    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi)
        img_path = os.path.join(temp_dir, f"page_{i+1}.png")
        pix.save(img_path)
        image_paths.append(img_path)

    merged_path = merge_images_grid(image_paths)
    shutil.rmtree(temp_dir, ignore_errors=True)
    return merged_path


# ====================================================
# Hierarchical Summarization
# ====================================================
def summarize_text_hierarchical(long_text, client=None, model="gpt-4o", chunk_size=8000):
    """Summarize long academic text hierarchically via chunked GPT summarization."""

    status_placeholder = st.empty()

    print(f"[Step 1] Data preprocessing...")
    # Step 1
    status_placeholder.write("[Step 1] Data preprocessing...")

    chunks = [long_text[i:i + chunk_size] for i in range(0, len(long_text), chunk_size)]
    summaries = []

    for i, chunk in enumerate(chunks):
        print(f"Summarizing chunk {i + 1}/{len(chunks)}...")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert research summarizer trained to preserve full technical accuracy. "
                        "Retain all essential details — model names, datasets, quantitative results, and ablation findings."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Summarize this passage:\n\n{chunk}\n\n"
                        "Focus on key details, simplify language but keep all results and comparisons."
                    )
                }
            ],
            temperature=0,
            max_tokens=1800
        )
        summaries.append(response.choices[0].message.content.strip())

    merged = "\n\n".join(summaries)
    print("Creating final hierarchical summary...")

    final_response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert academic summarizer. "
                    "Merge detailed summaries into a cohesive, structured overview of the paper."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Combine and refine the following summaries into a structured overview:\n\n{merged}"
                )
            }
        ],
        temperature=0,
        max_tokens=3000
    )

    status_placeholder.empty()

    return final_response.choices[0].message.content.strip()
