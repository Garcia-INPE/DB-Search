#!/usr/bin/env python3

import argparse
import re
import sys
from math import isclose
from pathlib import Path

import fitz  # PyMuPDF

try:
    sys.stdout.reconfigure(line_buffering=True, write_through=True)
    sys.stderr.reconfigure(line_buffering=True, write_through=True)
except Exception:
    pass

# Interactive execution from the project root needs src added before package imports.
if "__file__" not in globals() and str(Path.cwd() / "src") not in sys.path:
    sys.path.insert(0, str(Path.cwd() / "src"))

from db_search import fun_words as FWords
from db_search.paths import DATA_IN_DIR, ensure_src_on_path
from db_search.search_scope import get_scope_dataout_dir, resolve_search_scope

ensure_src_on_path(__file__ if "__file__" in globals() else None)

TITLE_FONT_SIZE = 9.871
META_FONT_SIZE = 7.678
FONT_TOLERANCE = 0.05
YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract Semantic Scholar records from scoped PDF exports."
    )
    parser.add_argument(
        "--ss-id",
        type=int,
        default=None,
        help="Search-string ID from search-strings CSV. Defaults to the last ID in search-strings CSV.",
    )
    parser.add_argument(
        "--config-csv",
        type=Path,
        default=None,
        help="Optional search-strings CSV path (default: src/datain/search_strings.csv; fallback: src/datain/config.csv or src/datain/CSV/config.csv).",
    )
    return parser.parse_args()


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


def extract_articles_from_pdf(pdf_path: Path) -> list[tuple[str, str]]:
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


def db_name_for_semantic_dir(dir_name: str, index: int) -> str:
    """Map directory names to SEMAN codes.

    Query-based names get deterministic order-based mapping.
    """
    return f"SEMAN{index}"


ARGS = parse_args()
try:
    SCOPE = resolve_search_scope(ARGS.ss_id, ARGS.config_csv)
except (FileNotFoundError, ValueError) as exc:
    raise SystemExit(f"[error] {exc}") from exc

DIR_DATA_OUT = get_scope_dataout_dir(SCOPE.ss_id)
DIR_DATA_IN = DIR_DATA_OUT / "PDF" / "SemanticScholar"
LEGACY_DIR_DATA_IN = DATA_IN_DIR / "PDF" / "SemanticScholar"
OUT_FILE = DIR_DATA_OUT / "SemanticScholar_from_pdfs.csv"

input_dir = DIR_DATA_IN if DIR_DATA_IN.is_dir() else LEGACY_DIR_DATA_IN
results: list[str] = []
input_groups: list[tuple[str, list[Path]]] = []

print(f"[info] SS_ID: {SCOPE.ss_id}")
print(f"[info] Input dir: {input_dir}")
print(f"[info] Output file: {OUT_FILE}")

if not input_dir.is_dir():
    print(f"[warn] no Semantic Scholar PDF directory found in: {DIR_DATA_IN}")
    print(f"[warn] legacy fallback also missing: {LEGACY_DIR_DATA_IN}")
else:
    direct_pdf_files = sorted(input_dir.glob("*.pdf"))
    nested_dirs = sorted(path for path in input_dir.iterdir() if path.is_dir())

    if direct_pdf_files:
        input_groups = [("SEMAN", direct_pdf_files)]
    else:
        input_groups = [
            (db_name_for_semantic_dir(semantic_dir.name, idx), sorted(semantic_dir.glob("*.pdf")))
            for idx, semantic_dir in enumerate(nested_dirs, start=1)
        ]

if input_dir.is_dir() and not input_groups:
    print(f"[warn] no Semantic Scholar PDFs found in: {input_dir}")

for db_name, pdf_files in input_groups:
    extracted = []
    for pdf_path in pdf_files:
        extracted.extend(extract_articles_from_pdf(pdf_path))

    print(f"{db_name}: {len(extracted)} papers")
    results.extend(f"{db_name};{year};{title}" for title, year in extracted)

DIR_DATA_OUT.mkdir(parents=True, exist_ok=True)
with open(OUT_FILE, "w", encoding="utf-8") as file:
    for article in results:
        file.write(f"{article}\n")

if results:
    print(f"[ok] extracted {len(results)} Semantic Scholar records")
    print(f"[out] {OUT_FILE}")
else:
    print(f"[warn] no Semantic Scholar records extracted; wrote empty file: {OUT_FILE}")
