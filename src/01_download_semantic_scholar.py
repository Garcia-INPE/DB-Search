#!/usr/bin/env python3
"""
Save the first N Semantic Scholar search-result pages as PDF files,
optionally extract YEAR and TITLE from the live page, and merge them into
SemanticScholar.csv.

By default, search scope is selected by SS_ID from src/datain/search_strings.csv
and outputs are written under src/dataout/SS{SS_ID}/.

Requirements:
  pip install playwright
  playwright install chromium

Usage examples:
    python 01_download_semantic_scholar.py
    python 01_download_semantic_scholar.py --ss-id 1
    python 01_download_semantic_scholar.py --ss-id 1 --query "survey review wildfire" --pages 20
    python 01_download_semantic_scholar.py --ss-id 1 --download-only

Output structure:
    src/dataout/SS{SS_ID}/PDF/SemanticScholar/P01.pdf
    src/dataout/SS{SS_ID}/SemanticScholar.csv
    src/dataout/SS{SS_ID}/logs/SemanticScholar/download_YYYYMMDD_HHMMSS.log

Note:
  This script reduces blocking risk with slow pacing, retries and jitter, but no script
  can guarantee an IP will never be blocked.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Callable
from urllib.parse import quote_plus

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

# Allow interactive execution from terminals not rooted at src/.
SRC_DIR = (
    os.path.dirname(os.path.abspath(__file__))
    if "__file__" in globals()
    else str(Path.cwd() / "src")
)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from db_search.search_scope import get_scope_dataout_dir, resolve_search_scope
from db_search.csv_records import merge_records_into_csv

try:
    sys.stdout.reconfigure(line_buffering=True, write_through=True)
    sys.stderr.reconfigure(line_buffering=True, write_through=True)
except Exception:
    pass


# Conservative defaults to reduce blocking risk.
DEFAULT_PAGES = 20
DEFAULT_MIN_DELAY = 8.0
DEFAULT_MAX_DELAY = 16.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT_MS = 45_000

BLOCKED_MARKERS = [
    "captcha",
    "verify you are human",
    "unusual traffic",
    "too many requests",
    "access denied",
]


def build_search_url(query: str, page_number: int) -> str:
    q = quote_plus(query.strip())
    return (
        "https://www.semanticscholar.org/search"
        f"?q={q}&sort=relevance&page={page_number}"
    )


def has_block_page(page) -> bool:
    text = page.content().lower()
    return any(marker in text for marker in BLOCKED_MARKERS)


def extract_total_results(page) -> int | None:
    """Best-effort extraction of total search result count from page text."""
    try:
        body_text = page.inner_text("body")
    except Exception:
        return None

    patterns = [
        r"\bof\s+([\d,]+)\s+results\b",
        r"\b([\d,]+)\s+results\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, body_text, flags=re.IGNORECASE)
        if match:
            try:
                return int(match.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


def human_wait(min_delay: float, max_delay: float) -> None:
    time.sleep(random.uniform(min_delay, max_delay))


def extract_page_results(page) -> list[dict[str, str]]:
    """Extract title and year from visible Semantic Scholar search results."""
    try:
        records = page.evaluate(
            """
            () => {
                const rows = [];
                const titleSelectors = [
                    'a[data-testid="title-link"]',
                    'h2 a',
                    'h3 a',
                    'a[href*="/paper/"]'
                ];
                const titleNodes = document.querySelectorAll(titleSelectors.join(','));
                const seen = new Set();

                titleNodes.forEach((node) => {
                    const title = (node.innerText || node.textContent || '').trim();
                    if (!title) {
                        return;
                    }

                    const key = title.toLowerCase();
                    if (seen.has(key)) {
                        return;
                    }
                    seen.add(key);

                    const container = node.closest(
                        'article, li, [data-testid="search-result"], .search-result, [data-selenium-selector="result-row"], [data-heap-nav]'
                    );
                    const metaText = container
                        ? (container.innerText || '')
                        : ((node.parentElement && node.parentElement.innerText) || '');

                    const yearMatch = metaText.match(/\\b(19|20)\\d{2}\\b/);
                    const year = yearMatch ? yearMatch[0] : '????';

                    rows.push({ title, year });
                });

                return rows;
            }
            """
        )
        return records if isinstance(records, list) else []
    except Exception as exc:
        print(f"  [warn] Could not extract results from page: {exc}")
        return []


def save_search_pages_as_pdf(
    query: str,
    pages: int,
    output_root: Path,
    csv_path: Path,
    min_delay: float,
    max_delay: float,
    max_retries: int,
    timeout_ms: int,
    headless: bool,
    extract_records: bool,
    log_dir: Path,
    log: Callable[[str], None],
) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    all_records: list[tuple[str, str, str]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 2400},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page = context.new_page()

        db_name = "SEMAN"

        total_results: int | None = None

        log(f"\nQuery: {query}")
        log(f"Output dir: {output_root}")

        for page_number in range(1, pages + 1):
            pdf_file = output_root / f"P{page_number:02d}.pdf"

            url = build_search_url(query, page_number)
            success = False

            for attempt in range(1, max_retries + 1):
                try:
                    log(
                        f"  [try {attempt}/{max_retries}] "
                        f"Capturing page {page_number:02d}: {url}"
                    )

                    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

                    # Give dynamic content time to settle.
                    human_wait(2.0, 4.5)

                    # Lightweight scroll to trigger lazy content on some pages.
                    page.mouse.wheel(0, 1500)
                    human_wait(1.0, 2.0)

                    if has_block_page(page):
                        raise RuntimeError("Possible anti-bot/block page detected")

                    if page_number == 1 and total_results is None:
                        total_results = extract_total_results(page)
                        total_label = (
                            str(total_results)
                            if total_results is not None
                            else "unknown"
                        )
                        log(f"  [info] Total results reported: {total_label}")

                    if extract_records:
                        page_records = extract_page_results(page)
                        if page_number == 1 and len(page_records) == 0:
                            debug_html = log_dir / "semantic_scholar_debug_page01.html"
                            debug_html.write_text(page.content(), encoding="utf-8")
                            log(f"  [warn] Extracted 0 results on page 01. Saved debug HTML: {debug_html}")

                        all_records.extend(
                            (db_name, rec.get("year", "????"), rec.get("title", ""))
                            for rec in page_records
                            if rec.get("title")
                        )
                        log(f"  [info] Extracted {len(page_records)} result(s) from page {page_number:02d}")

                    if pdf_file.exists():
                        pdf_file.unlink()
                        log(f"  [info] Overwriting existing {pdf_file.name}")

                    page.pdf(
                        path=str(pdf_file),
                        format="A4",
                        print_background=True,
                        margin={"top": "8mm", "right": "8mm", "bottom": "8mm", "left": "8mm"},
                    )

                    log(f"  [ok] Saved {pdf_file.name}")
                    success = True
                    break

                except (PlaywrightTimeoutError, RuntimeError) as exc:
                    backoff = random.uniform(15.0, 35.0) * attempt
                    log(f"  [warn] {exc}. Backoff {backoff:.1f}s before retry...")
                    time.sleep(backoff)

            if not success:
                log(f"  [error] Failed page {page_number:02d} after retries")

            # Main pacing control between pages.
            human_wait(min_delay, max_delay)

        if extract_records:
            total_rows, added_rows = merge_records_into_csv(csv_path, all_records)
            if total_results and total_results > 0 and len(all_records) == 0:
                log("[warn] Total results were reported, but zero records were extracted. Selectors may need an update.")
            log(f"\n[info] Parsed {len(all_records)} live record(s)")
            log(f"[info] CSV now has {total_rows} row(s); added {added_rows}")
        else:
            log("\n[info] Download-only mode: CSV extraction skipped.")
        log("\n[done] Semantic Scholar page capture completed.")

        context.close()
        browser.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Save Semantic Scholar result pages to PDF with throttling and retries."
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
    parser.add_argument(
        "--query",
        default=None,
        help="Single query string to run. Defaults to SEARCH_STRING for SS_ID from search-strings CSV.",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=DEFAULT_PAGES,
        help=f"How many result pages to save for the query (default: {DEFAULT_PAGES}).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Root output directory (default: src/dataout/SS{SS_ID}/PDF/SemanticScholar).",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="CSV output file for extracted titles/years (default: src/dataout/SS{SS_ID}/SemanticScholar.csv).",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=None,
        help="Directory for run logs (default: src/dataout/SS{SS_ID}/logs/SemanticScholar).",
    )
    parser.add_argument(
        "--min-delay",
        type=float,
        default=DEFAULT_MIN_DELAY,
        help=f"Minimum delay (seconds) between page requests (default: {DEFAULT_MIN_DELAY}).",
    )
    parser.add_argument(
        "--max-delay",
        type=float,
        default=DEFAULT_MAX_DELAY,
        help=f"Maximum delay (seconds) between page requests (default: {DEFAULT_MAX_DELAY}).",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help=f"Retry attempts per page (default: {DEFAULT_MAX_RETRIES}).",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=DEFAULT_TIMEOUT_MS,
        help=f"Navigation timeout in ms (default: {DEFAULT_TIMEOUT_MS}).",
    )
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Run browser with GUI (headless by default).",
    )
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Download PDFs only and skip live extraction into SemanticScholar.csv.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        scope = resolve_search_scope(args.ss_id, args.config_csv)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    scope_dir = get_scope_dataout_dir(scope.ss_id)
    output_root = args.output if args.output is not None else (scope_dir / "PDF" / "SemanticScholar")
    csv_path = args.csv if args.csv is not None else (scope_dir / "SemanticScholar.csv")
    log_dir = args.log_dir if args.log_dir is not None else (scope_dir / "logs" / "SemanticScholar")

    if args.pages < 1:
        print("--pages must be >= 1", file=sys.stderr)
        return 2

    if args.min_delay <= 0 or args.max_delay <= 0:
        print("--min-delay and --max-delay must be > 0", file=sys.stderr)
        return 2

    if args.min_delay > args.max_delay:
        print("--min-delay cannot be greater than --max-delay", file=sys.stderr)
        return 2

    query = args.query.strip() if args.query else scope.search_string.strip()
    if not query:
        print("--query cannot be empty", file=sys.stderr)
        return 2

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"download_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_fh = log_file.open("w", encoding="utf-8")

    def log(message: str) -> None:
        print(message)
        log_fh.write(f"{message}\n")
        log_fh.flush()

    log(f"[info] Run log: {log_file}")
    log(f"[info] SS_ID: {scope.ss_id}")
    log(f"[info] Search-strings CSV: {scope.config_path}")
    log(f"[info] Extract mode: {'disabled' if args.download_only else 'enabled'}")

    try:
        save_search_pages_as_pdf(
            query=query,
            pages=args.pages,
            output_root=output_root,
            csv_path=csv_path,
            min_delay=args.min_delay,
            max_delay=args.max_delay,
            max_retries=args.max_retries,
            timeout_ms=args.timeout_ms,
            headless=not args.headful,
            extract_records=not args.download_only,
            log_dir=log_dir,
            log=log,
        )
    finally:
        log_fh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
