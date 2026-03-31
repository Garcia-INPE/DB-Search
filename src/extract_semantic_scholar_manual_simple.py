#!/usr/bin/env python3
"""Simple Semantic Scholar PDF parser (standalone).

Extract YEAR and TITLE from PDFs located in:
/home/jrmgarcia/ProjDocs/DB_Search/src/datain/SS01/PDF/SemanticScholar/manual

No project-module imports are used; only standard library + PyMuPDF.
"""

from __future__ import annotations

import re
import sys
from math import isclose
from pathlib import Path

import fitz  # PyMuPDF

INPUT_DIR = Path(
    "/home/jrmgarcia/ProjDocs/DB_Search/src/datain/SS01/PDF/SemanticScholar/manual"
)
OUTPUT_CSV = INPUT_DIR / "SemanticScholar_manual_extracted.csv"
DB_NAME = "SEMAN"

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

def block_text(block: dict) -> str:
    return " ".join(
        span["text"].strip()
        for line in block.get("lines", [])
        for span in line.get("spans", [])
        if span.get("text", "").strip()
    )


def block_size(block: dict) -> float | None:
    lines = block.get("lines", [])
    if not lines or not lines[0].get("spans"):
        return None
    return lines[0]["spans"][0].get("size")


def is_title_block(block: dict) -> bool:
    text = block_text(block)
    size = block_size(block)
    return (
        bool(text)
        and size is not None
        and text.lower() not in EXCLUDED_TITLES
        and isclose(size, TITLE_FONT_SIZE, abs_tol=FONT_TOLERANCE)
    )


def clean_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title).strip()
    title = title.replace(";", ",")
    return title


def extract_articles_from_pdf(pdf_path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []

    with fitz.open(pdf_path) as document:
        for page in document:
            current_title = ""
            current_year = "????"
            has_metadata = False

            page_dict = page.get_text("dict")
            for block in page_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue

                text = block_text(block)
                if not text:
                    continue

                if any(marker in text for marker in STOP_TEXT_MARKERS):
                    break

                if is_title_block(block):
                    if current_title and has_metadata:
                        rows.append((current_year, clean_title(current_title)))

                    current_title = text
                    current_year = "????"
                    has_metadata = False
                    continue

                size = block_size(block)
                if current_title and size is not None and isclose(size, META_FONT_SIZE, abs_tol=FONT_TOLERANCE):
                    has_metadata = True
                    year_matches = YEAR_PATTERN.findall(text)
                    if year_matches:
                        current_year = year_matches[-1]

            if current_title and has_metadata:
                rows.append((current_year, clean_title(current_title)))

    return rows


def deduplicate(rows: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    deduped: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()

    for db_name, year, title in rows:
        key = (db_name.casefold(), title.casefold())
        if key in seen:
            continue
        seen.add(key)
        deduped.append((db_name, year, title))
    return deduped


def write_csv(rows: list[tuple[str, str, str]], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8") as handle:
        for db_name, year, title in rows:
            handle.write(f"{db_name};{year};{title}\n")


def main() -> int:
    input_dir = INPUT_DIR
    output_csv = OUTPUT_CSV
    db_name = DB_NAME

    print(f"[info] Input dir: {input_dir}")
    print(f"[info] Output CSV: {output_csv}")

    if not input_dir.is_dir():
        print(f"[error] Input directory does not exist: {input_dir}", file=sys.stderr)
        return 2

    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"[warn] No PDF files found in: {input_dir}")
        write_csv([], output_csv)
        print(f"[out] {output_csv}")
        return 0

    extracted_rows: list[tuple[str, str, str]] = []
    for pdf_path in pdf_files:
        records = extract_articles_from_pdf(pdf_path)
        print(f"[info] {pdf_path.name}: {len(records)} record(s)")
        extracted_rows.extend((db_name, year, title) for year, title in records)

    unique_rows = deduplicate(extracted_rows)
    write_csv(unique_rows, output_csv)

    print(f"[ok] Extracted {len(unique_rows)} unique record(s)")
    print(f"[out] {output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
