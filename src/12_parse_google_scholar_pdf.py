#!/usr/bin/env python3
"""Parse saved Google Scholar result PDFs and merge records into GoogleScholar.csv.

By default, search scope is selected by SS_ID from src/datain/search_strings.csv
and outputs are written under src/dataout/SS{SS_ID}/.

Input priority:
1. src/dataout/SS{SS_ID}/PDF/GoogleScholar/
2. src/datain/SS{SS_ID}/PDF/GoogleScholar/
3. src/datain/PDF/GoogleScholar/ (legacy fallback)

Output:
    src/dataout/SS{SS_ID}/GoogleScholar.csv
"""

from __future__ import annotations

import argparse
import re
import sys
from html import unescape
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import Request, urlopen

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
from db_search.search_scope import get_scope_dataout_dir, resolve_search_scope

ensure_src_on_path(__file__ if "__file__" in globals() else None)

TRUNCATION_PREFIX_RE = re.compile(r"^\s*(?:(?:\.\.\.|…|\.)\s*[:;\-–—]*\s*)+")
TITLE_META_PATTERNS = [
    re.compile(r'<meta[^>]+name=["\']citation_title["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<meta[^>]+name=["\']dc\.title["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<title[^>]*>(.*?)</title>', re.IGNORECASE | re.DOTALL),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parse Google Scholar PDFs and merge records into GoogleScholar.csv."
    )
    parser.add_argument("--ss-id", type=int, default=None)
    parser.add_argument("--config-csv", type=Path, default=None)
    parser.add_argument("--input-dir", type=Path, default=None)
    parser.add_argument("--csv", type=Path, default=None)
    parser.add_argument("--log-dir", type=Path, default=None)
    return parser.parse_args()


def strip_google_scholar_truncation_prefix(title: str) -> str:
    return TRUNCATION_PREFIX_RE.sub("", title).strip()


def get_block_uri(block: dict, page_links: list[dict]) -> str | None:
    rect = fitz.Rect(block["bbox"])
    uris = []
    for link in page_links:
        uri = link.get("uri")
        if not uri or uri.startswith("javascript:"):
            continue
        link_rect = link.get("from")
        if not link_rect:
            continue
        if rect.intersects(link_rect):
            uris.append(uri)
    return next(iter(dict.fromkeys(uris)), None)


def normalize_article_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    redirect_url = parse_qs(parsed.query).get("redirect_uri")
    if redirect_url:
        return unquote(redirect_url[0])
    return url


def fetch_title_from_url(url: str | None, resolved_title_cache: dict[str, str | None]) -> str | None:
    normalized_url = normalize_article_url(url)
    if not normalized_url:
        return None
    if normalized_url in resolved_title_cache:
        return resolved_title_cache[normalized_url]

    try:
        request = Request(normalized_url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=15) as response:
            raw_html = response.read(512_000)
            encoding = response.headers.get_content_charset() or "utf-8"
        html = raw_html.decode(encoding, errors="ignore")
    except Exception:
        resolved_title_cache[normalized_url] = None
        return None

    for pattern in TITLE_META_PATTERNS:
        match = pattern.search(html)
        if not match:
            continue
        candidate = unescape(match.group(1))
        candidate = re.sub(r"\s+", " ", candidate).strip()
        if candidate:
            cleaned = FWords.adj_title(candidate)
            resolved_title_cache[normalized_url] = cleaned
            return cleaned

    resolved_title_cache[normalized_url] = None
    return None


def extract_records_from_pdf(
    pdf_path: Path,
    resolved_title_cache: dict[str, str | None],
    truncated_title_rows: list[tuple[str, int, str, str, str | None]],
) -> list[tuple[str, str, str]]:
    titles: list[str] = []
    years: list[str] = []

    with fitz.open(pdf_path) as document:
        for page_index, page in enumerate(document):
            page_blocks = page.get_text("dict")["blocks"]
            page_links = page.get_links()

            for block in page_blocks:
                if block.get("type") != 0 or not block.get("lines"):
                    continue

                size = block["lines"][0]["spans"][0]["size"]
                color = block["lines"][0]["spans"][0]["color"]

                if size == 12:
                    title = ""
                    for line_index, line in enumerate(block["lines"]):
                        if line_index > 0:
                            title += " "
                        for span in line["spans"]:
                            title += span["text"]

                    raw_title = title
                    title = strip_google_scholar_truncation_prefix(raw_title)
                    title = FWords.adj_title(title)
                    title_url = get_block_uri(block, page_links)
                    cleaned_title = title
                    if raw_title != title:
                        resolved_title = fetch_title_from_url(title_url, resolved_title_cache)
                        if resolved_title:
                            cleaned_title = resolved_title
                    if cleaned_title != raw_title:
                        truncated_title_rows.append((pdf_path.name, page_index, raw_title, cleaned_title, title_url))
                    titles.append(cleaned_title)

                if color == 32768:
                    metadata = ""
                    for line in block["lines"]:
                        for span in line["spans"]:
                            if span["color"] == 32768:
                                metadata += span["text"]
                    all_dates = re.findall(r"\b(?:19|20)\d{2}\b", metadata)
                    years.append(all_dates[-1].strip() if all_dates else "????")

    if len(titles) != len(years):
        raise RuntimeError(
            f"Mismatch between extracted titles ({len(titles)}) and years ({len(years)}) in {pdf_path.name}"
        )

    return [("SCHOLA", year, title) for year, title in zip(years, titles)]


def main() -> int:
    args = parse_args()
    try:
        scope = resolve_search_scope(args.ss_id, args.config_csv)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2

    scope_dir = get_scope_dataout_dir(scope.ss_id)
    input_dir = args.input_dir if args.input_dir is not None else (scope_dir / "PDF" / "GoogleScholar")
    if not input_dir.is_dir():
        scoped_datain_dir = DATA_IN_DIR / f"SS{scope.ss_id}" / "PDF" / "GoogleScholar"
        legacy_datain_dir = DATA_IN_DIR / "PDF" / "GoogleScholar"
        if scoped_datain_dir.is_dir():
            input_dir = scoped_datain_dir
        elif legacy_datain_dir.is_dir():
            input_dir = legacy_datain_dir

    csv_path = args.csv if args.csv is not None else (scope_dir / "GoogleScholar.csv")
    log_dir = args.log_dir if args.log_dir is not None else (scope_dir / "logs" / "GoogleScholar")
    print(f"[info] SS_ID: {scope.ss_id}")
    print(f"[info] Input dir: {input_dir}")
    print(f"[info] CSV output: {csv_path}")

    if not input_dir.is_dir():
        print(f"[error] Missing Google Scholar PDF directory: {input_dir}", file=sys.stderr)
        return 2

    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"[warn] No Google Scholar PDFs found in: {input_dir}")
        return 0

    records: list[tuple[str, str, str]] = []
    resolved_title_cache: dict[str, str | None] = {}
    truncated_title_rows: list[tuple[str, int, str, str, str | None]] = []
    for pdf_path in pdf_files:
        extracted = extract_records_from_pdf(pdf_path, resolved_title_cache, truncated_title_rows)
        print(f"[info] {pdf_path.name}: {len(extracted)} record(s)")
        records.extend(extracted)

    total_records, added_records = merge_records_into_csv(csv_path, records)
    if truncated_title_rows:
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "GoogleScholar_truncated_titles.log").open("w", encoding="utf-8") as handle:
            for pdf_name, page_index, raw_title, cleaned_title, title_url in truncated_title_rows:
                handle.write(
                    f"file={pdf_name} page={page_index} | raw={raw_title} | cleaned={cleaned_title} | url={title_url}\n"
                )

    print(f"[ok] Parsed {len(records)} Google Scholar PDF record(s)")
    print(f"[ok] CSV now has {total_records} row(s); added {added_records}")
    print(f"[out] {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())