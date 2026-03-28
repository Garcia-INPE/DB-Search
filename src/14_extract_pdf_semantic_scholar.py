import re
import sys
from math import isclose
from pathlib import Path
import fitz  # PyMuPDF

# Interactive execution from the project root needs src added before package imports.
if "__file__" not in globals():
    sys.path.insert(0, str(Path.cwd() / "src"))

from db_search import fun_words as FWords
from db_search.paths import DATA_IN_DIR, DATA_OUT_DIR, ensure_src_on_path

ensure_src_on_path(__file__ if "__file__" in globals() else None)

DIR_DATA_IN = DATA_IN_DIR / "PDF" / "SemanticScholar"
DIR_DATA_OUT = DATA_OUT_DIR

TITLE_FONT_SIZE = 9.871
META_FONT_SIZE = 7.678
FONT_TOLERANCE = 0.05
YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")
DIR_PATTERN = re.compile(r"^SS(\d{2})_")
STOP_TEXT_MARKERS = {
    "Stay Connected With Semantic Scholar",
    "Proudly built by Ai2",
}
EXCLUDED_TITLES = {
    "what is semantic scholar?",
    "about",
    "product",
    "api",
    "research",
    "help",
    "recent publications",
    "quasar surveys",
}


def block_text(block):
    return " ".join(
        span["text"].strip()
        for line in block["lines"]
        for span in line["spans"]
        if span["text"].strip()
    )


def block_size(block):
    return block["lines"][0]["spans"][0]["size"]


def is_title_block(block):
    text = block_text(block)
    size = block_size(block)
    return (
        bool(text)
        and text.lower() not in EXCLUDED_TITLES
        and isclose(size, TITLE_FONT_SIZE, abs_tol=FONT_TOLERANCE)
    )


def extract_articles_from_pdf(pdf_path):
    articles = []

    with fitz.open(pdf_path) as document:
        for page in document:
            current_title = ""
            current_year = "????"
            has_metadata = False

            for block in page.get_text("dict")["blocks"]:
                if block.get("type") != 0 or not block.get("lines"):
                    continue

                text = block_text(block)
                if not text:
                    continue

                if any(marker in text for marker in STOP_TEXT_MARKERS):
                    break

                if is_title_block(block):
                    if current_title and has_metadata:
                        articles.append((FWords.adj_title(current_title), current_year))

                    current_title = text
                    current_year = "????"
                    has_metadata = False
                    continue

                if current_title and isclose(block_size(block), META_FONT_SIZE, abs_tol=FONT_TOLERANCE):
                    has_metadata = True
                    year_matches = YEAR_PATTERN.findall(text)
                    if year_matches:
                        current_year = year_matches[-1]

            if current_title and has_metadata:
                articles.append((FWords.adj_title(current_title), current_year))

    return articles


results = []
semantic_dirs = sorted(
    path for path in DIR_DATA_IN.iterdir()
    if path.is_dir() and DIR_PATTERN.match(path.name)
)

for semantic_dir in semantic_dirs:
    match = DIR_PATTERN.match(semantic_dir.name)
    dir_number = match.group(1)
    # Use 1-digit number for db name if dir number is less than 10, otherwise use 2-digit number
    if dir_number.startswith("0"):
        db_name = f"SEMAN{dir_number[1]}"
    else:
        db_name = f"SEMAN{dir_number}"

    pdf_files = sorted(semantic_dir.glob("*.pdf"))
    extracted = []
    for pdf_path in pdf_files:
        extracted.extend(extract_articles_from_pdf(pdf_path))

    print(f"{db_name}: {len(extracted)} papers")

    results.extend(
        f"{db_name};{year};{title}"
        for title, year in extracted
    )


with open(DIR_DATA_OUT / "SemanticScholar.csv", "w", encoding="utf-8") as file:
    for article in results:
        file.write(f"{article}\n")
