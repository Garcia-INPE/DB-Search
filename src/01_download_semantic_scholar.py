#!/usr/bin/env python3
"""
Save the first N Semantic Scholar search-result pages as PDF files.

Requirements:
  pip install playwright
  playwright install chromium

Usage examples:
    python 01_download_semantic_scholar.py
    python 01_download_semantic_scholar.py --queries "wildfire spread" "fire behavior model"
    python 01_download_semantic_scholar.py --queries-file queries.txt --pages 20

Output structure:
    src/datain/PDF/SemanticScholar/<query_string>/SS_page_01.pdf

Note:
  This script reduces blocking risk with slow pacing, retries and jitter, but no script
  can guarantee an IP will never be blocked.
"""

from __future__ import annotations

import argparse
import csv
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable, List
from urllib.parse import quote_plus

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


# Easy-to-configure default query list.
DEFAULT_QUERIES = [
    "wildfire spread prediction",
    "forest fire machine learning",
]

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


def normalize_query_dirname(query: str) -> str:
    """Build a human-readable directory name based on the query string.

    We keep the query text as-is as much as possible and only sanitize path
    separators so each query gets its own valid directory.
    """
    cleaned = query.strip()
    cleaned = re.sub(r"[\\/]+", "-", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or "query"


def build_search_url(query: str, page_number: int) -> str:
    q = quote_plus(query.strip())
    return (
        "https://www.semanticscholar.org/search"
        f"?q={q}&sort=relevance&page={page_number}"
    )


def read_queries_from_file(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"Queries file not found: {path}")

    queries: List[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        queries.append(line)
    return queries


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


def write_summary_rows(summary_file: Path, rows: List[dict]) -> None:
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "run_timestamp",
        "query",
        "query_dir",
        "total_results",
        "pages_target",
    ]

    write_header = not summary_file.exists()
    with summary_file.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def human_wait(min_delay: float, max_delay: float) -> None:
    time.sleep(random.uniform(min_delay, max_delay))


def ensure_queries(cli_queries: Iterable[str], queries_file: Path | None) -> List[str]:
    if cli_queries:
        return [q.strip() for q in cli_queries if q.strip()]

    if queries_file is not None:
        return read_queries_from_file(queries_file)

    return [q.strip() for q in DEFAULT_QUERIES if q.strip()]


def save_search_pages_as_pdf(
    queries: List[str],
    pages: int,
    output_root: Path,
    min_delay: float,
    max_delay: float,
    max_retries: int,
    timeout_ms: int,
    headless: bool,
) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    run_timestamp = datetime.now().isoformat(timespec="seconds")
    summary_rows: List[dict] = []

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

        for query in queries:
            safe_name = normalize_query_dirname(query)
            query_dir = output_root / safe_name
            query_dir.mkdir(parents=True, exist_ok=True)

            total_results: int | None = None

            print(f"\nQuery: {query}")
            print(f"Output dir: {query_dir}")

            for page_number in range(1, pages + 1):
                pdf_file = query_dir / f"SS_page_{page_number:02d}.pdf"
                if pdf_file.exists():
                    print(f"  [skip] Page {page_number:02d} already exists")
                    continue

                url = build_search_url(query, page_number)
                success = False

                for attempt in range(1, max_retries + 1):
                    try:
                        print(
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
                            print(f"  [info] Total results reported: {total_label}")

                        page.pdf(
                            path=str(pdf_file),
                            format="A4",
                            print_background=True,
                            margin={"top": "8mm", "right": "8mm", "bottom": "8mm", "left": "8mm"},
                        )

                        print(f"  [ok] Saved {pdf_file.name}")
                        success = True
                        break

                    except (PlaywrightTimeoutError, RuntimeError) as exc:
                        backoff = random.uniform(15.0, 35.0) * attempt
                        print(f"  [warn] {exc}. Backoff {backoff:.1f}s before retry...")
                        time.sleep(backoff)

                if not success:
                    print(f"  [error] Failed page {page_number:02d} after retries")

                # Main pacing control between pages.
                human_wait(min_delay, max_delay)

            summary_rows.append(
                {
                    "run_timestamp": run_timestamp,
                    "query": query,
                    "query_dir": safe_name,
                    "total_results": (
                        str(total_results)
                        if total_results is not None
                        else "unknown"
                    ),
                    "pages_target": str(pages),
                }
            )

        summary_file = output_root / "SemanticScholar_query_totals.csv"
        write_summary_rows(summary_file, summary_rows)
        print(f"\n[done] Query totals logged to: {summary_file}")

        context.close()
        browser.close()


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_output = script_dir / "datain" / "PDF" / "SemanticScholar"

    parser = argparse.ArgumentParser(
        description="Save Semantic Scholar result pages to PDF with throttling and retries."
    )
    parser.add_argument(
        "--queries",
        nargs="*",
        default=[],
        help="Query strings to run. If omitted, DEFAULT_QUERIES is used.",
    )
    parser.add_argument(
        "--queries-file",
        type=Path,
        default=None,
        help="Text file with one query per line (# for comments).",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=DEFAULT_PAGES,
        help=f"How many result pages to save per query (default: {DEFAULT_PAGES}).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help=f"Root output directory (default: {default_output}).",
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.pages < 1:
        print("--pages must be >= 1", file=sys.stderr)
        return 2

    if args.min_delay <= 0 or args.max_delay <= 0:
        print("--min-delay and --max-delay must be > 0", file=sys.stderr)
        return 2

    if args.min_delay > args.max_delay:
        print("--min-delay cannot be greater than --max-delay", file=sys.stderr)
        return 2

    try:
        queries = ensure_queries(args.queries, args.queries_file)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if not queries:
        print("No queries found. Provide --queries or --queries-file.", file=sys.stderr)
        return 2

    save_search_pages_as_pdf(
        queries=queries,
        pages=args.pages,
        output_root=args.output,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        max_retries=args.max_retries,
        timeout_ms=args.timeout_ms,
        headless=not args.headful,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
