#!/usr/bin/env python3
"""Parse saved Semantic Scholar result PDFs and merge records into SemanticScholar.csv.

By default, search scope is selected by SS_ID from src/datain/search_strings.csv
and outputs are written under src/dataout/SS{SS_ID}/.

Input priority:
1. src/datain/SS{SS_ID:02d}/PDF/SemanticScholar/manual/
2. src/datain/SS{SS_ID}/PDF/SemanticScholar/manual/
3. src/dataout/SS{SS_ID}/PDF/SemanticScholar/
4. src/datain/PDF/SemanticScholar/ (legacy fallback)

Output:
    src/dataout/SS{SS_ID}/SemanticScholar.csv
"""

from __future__ import annotations

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

if "__file__" not in globals() and str(Path.cwd() / "src") not in sys.path:
    sys.path.insert(0, str(Path.cwd() / "src"))

from db_search import fun_words as FWords
from db_search.csv_records import merge_records_into_csv
from db_search.paths import DATA_IN_DIR, ensure_src_on_path
from db_search.search_scope import get_scope_dataout_dir, get_scope_datain_dir, resolve_search_scope

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
        description="Parse Semantic Scholar PDFs and merge records into SemanticScholar.csv."
    )
    parser.add_argument("--ss-id", type=int, default=None)
    parser.add_argument("--config-csv", type=Path, default=None)
    parser.add_argument("--input-dir", type=Path, default=None)
    parser.add_argument("--csv", type=Path, default=None)
    return parser.parse_args()


def block_text(block: dict) -> str:
    return " ".join(
        span["text"].strip()
        for line in block["lines"]
        for span in line["spans"]
        if span["text"].strip()
    )


def block_size(block: dict) -> float:
    return block["lines"][0]["spans"][0]["size"]


def is_title_block(block: dict) -> bool:
    text = block_text(block)
    size = block_size(block)
    return (
        bool(text)
        and text.lower() not in EXCLUDED_TITLES
        and isclose(size, TITLE_FONT_SIZE, abs_tol=FONT_TOLERANCE)
    )


def extract_articles_from_pdf(pdf_path: Path) -> list[tuple[str, str]]:
    #pdf_path = pdf_files[0]
    articles: list[tuple[str, str]] = []

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
                        articles.append(
                            (FWords.adj_title(current_title), current_year))

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
                articles.append(
                    (FWords.adj_title(current_title), current_year))

    return articles


#def main() -> int:
args = parse_args()
try:
    scope = resolve_search_scope(args.ss_id, args.config_csv)
except (FileNotFoundError, ValueError) as exc:
    print(f"[error] {exc}", file=sys.stderr)
    return 2

scope_dir = get_scope_dataout_dir(scope.ss_id)
scoped_manual_input_dir_zero = DATA_IN_DIR / f"SS{scope.ss_id:02d}" / "PDF" / "SemanticScholar" / "manual"
scoped_manual_input_dir = get_scope_datain_dir(scope.ss_id) / "PDF" / "SemanticScholar" / "manual"
if args.input_dir is not None:
    input_dir = args.input_dir
else:
    input_dir = scoped_manual_input_dir_zero
    if not input_dir.is_dir():
        input_dir = scoped_manual_input_dir
    if not input_dir.is_dir():
        scoped_dataout_input_dir = scope_dir / "PDF" / "SemanticScholar"
        legacy_input_dir = DATA_IN_DIR / "PDF" / "SemanticScholar"
        if scoped_dataout_input_dir.is_dir():
            input_dir = scoped_dataout_input_dir
        elif legacy_input_dir.is_dir():
            input_dir = legacy_input_dir
        else:
            input_dir.mkdir(parents=True, exist_ok=True)
            print(
                f"[warn] Missing Semantic Scholar PDF directory. Created: {input_dir}")

csv_path = args.csv if args.csv is not None else (
    scope_dir / "SemanticScholar.csv")
print(f"[info] SS_ID: {scope.ss_id}")
print(f"[info] Input dir: {input_dir}")
print(f"[info] CSV output: {csv_path}")

pdf_files = sorted(input_dir.glob("*.pdf"))
if not pdf_files:
    print(f"[warn] No Semantic Scholar PDFs found in: {input_dir}")
    return 0

records: list[tuple[str, str, str]] = []
for pdf_path in pdf_files:
    extracted = extract_articles_from_pdf(pdf_path)
    print(f"[info] {pdf_path.name}: {len(extracted)} record(s)")
    records.extend(("SEMAN", year, title) for title, year in extracted)

total_records, added_records = merge_records_into_csv(csv_path, records)
print(f"[ok] Parsed {len(records)} Semantic Scholar PDF record(s)")
print(f"[ok] CSV now has {total_records} row(s); added {added_records}")
print(f"[out] {csv_path}")



#if __name__ == "__main__":
#    raise SystemExit(main())
