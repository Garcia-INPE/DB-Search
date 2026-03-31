#!/usr/bin/env python3
"""Save Google Scholar result pages as PDFs,
optionally extract YEAR and TITLE from live results, and merge them into
GoogleScholar.csv.

By default, search scope is selected by SS_ID from src/datain/search_strings.csv
and outputs are written under src/dataout/SS{SS_ID}/.

Also supports OpenAlex API mode to fetch YEAR and TITLE directly (no browser),
writing the same CSV format for downstream compatibility.

Requirements:
  pip install playwright
  playwright install chromium

Usage examples:
  python src/02_download_google_scholar_pdf.py --query "survey review wildfire"
        python src/02_download_google_scholar_pdf.py --ss-id 1 --query "survey review wildfire"
    python src/02_download_google_scholar_pdf.py --query "survey review wildfire" --pages 10
    python src/02_download_google_scholar_pdf.py --ss-id 1 --download-only
    python src/02_download_google_scholar_pdf.py --safe --headless
    python src/02_download_google_scholar_pdf.py --medium --headful
    python src/02_download_google_scholar_pdf.py --fast --headful

Output structure:
        src/dataout/SS{SS_ID}/PDF/GoogleScholar/P01.pdf
        src/dataout/SS{SS_ID}/GoogleScholar.csv
        src/dataout/SS{SS_ID}/logs/GoogleScholar/download_YYYYMMDD_HHMMSS.log

Note:
  Google Scholar may present captcha or anti-bot pages. This script uses slow pacing,
  retries and browser PDF export, but cannot guarantee uninterrupted access.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import random
import re
import sys
import time
from pathlib import Path
from typing import Callable
from urllib.parse import quote_plus, urlencode
from urllib.request import Request, urlopen

# Allow interactive execution from terminals not rooted at src/.
SRC_DIR = Path(__file__).resolve().parent if "__file__" in globals() else (Path.cwd() / "src")
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from db_search.search_scope import get_scope_dataout_dir, resolve_search_scope
from db_search.csv_records import merge_records_into_csv

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_IMPORT_ERROR = None
except ModuleNotFoundError as exc:
    PlaywrightTimeoutError = TimeoutError
    sync_playwright = None
    PLAYWRIGHT_IMPORT_ERROR = exc

try:
    sys.stdout.reconfigure(line_buffering=True, write_through=True)
    sys.stderr.reconfigure(line_buffering=True, write_through=True)
except Exception:
    pass


DEFAULT_PAGES = 10
DEFAULT_RESULTS_PER_PAGE = 20  # Google Scholar supports up to 20; 20x10 = 200 total
DEFAULT_MIN_DELAY = 8.0
DEFAULT_MAX_DELAY = 16.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT_MS = 45_000
# Default profile is medium (balanced speed/risk).
DEFAULT_PROFILE = "medium"
DEFAULT_SOURCE = "scholar"
OPENALEX_BASE_URL = "https://api.openalex.org/works"

# Optional medium profile for faster runs with moderate blocking risk.
MEDIUM_MIN_DELAY = 4.0
MEDIUM_MAX_DELAY = 8.0
MEDIUM_SETTLE_MIN = 1.2
MEDIUM_SETTLE_MAX = 2.5
MEDIUM_SCROLL_MIN = 0.6
MEDIUM_SCROLL_MAX = 1.2
MEDIUM_BACKOFF_MIN = 8.0
MEDIUM_BACKOFF_MAX = 16.0
MEDIUM_MAX_RETRIES = 3

# Optional fast profile for quicker runs with higher blocking risk.
FAST_MIN_DELAY = 2.0
FAST_MAX_DELAY = 4.0
FAST_SETTLE_MIN = 0.8
FAST_SETTLE_MAX = 1.6
FAST_SCROLL_MIN = 0.3
FAST_SCROLL_MAX = 0.8
FAST_BACKOFF_MIN = 5.0
FAST_BACKOFF_MAX = 10.0
FAST_MAX_RETRIES = 2

BLOCKED_MARKERS = [
    "captcha",
    "verify you're not a robot",
    "unusual traffic",
    "not a robot",
    "detected unusual traffic",
]

RESULT_SELECTORS = [
    "div.gs_r.gs_or",
    "div.gs_ri",
    "#gs_res_ccl_mid",
]


def build_search_url(query: str, page_index: int, num: int = DEFAULT_RESULTS_PER_PAGE) -> str:
    start = page_index * num
    q = quote_plus(query.strip())
    return f"https://scholar.google.com/scholar?q={q}&hl=en&num={num}&start={start}"


def human_wait(min_delay: float, max_delay: float) -> None:
    time.sleep(random.uniform(min_delay, max_delay))


def has_block_page(page) -> bool:
    try:
        content = page.content().lower()
    except Exception:
        return False
    return any(marker in content for marker in BLOCKED_MARKERS)


def try_accept_consent(page, timeout_ms: int, log: Callable[[str], None]) -> None:
    """Best-effort acceptance of consent dialogs that block result rendering."""
    consent_texts = [
        "I agree",
        "Accept all",
        "I accept",
        "Accept",
        "Agree",
    ]
    for text in consent_texts:
        try:
            btn = page.get_by_role("button", name=text)
            if btn.count() > 0:
                btn.first.click(timeout=min(4_000, timeout_ms))
                human_wait(0.4, 1.0)
                log(f"  [info] Clicked consent button: {text}")
                return
        except Exception:
            continue


def wait_for_results(page, timeout_ms: int, log: Callable[[str], None]) -> None:
    try_accept_consent(page, timeout_ms, log)

    per_selector_timeout = max(1_500, min(8_000, timeout_ms // max(1, len(RESULT_SELECTORS))))
    for selector in RESULT_SELECTORS:
        try:
            page.wait_for_selector(selector, state="attached", timeout=per_selector_timeout)
            return
        except Exception:
            continue

    # Fallback: detect result cards by count even if visibility state is inconsistent.
    try:
        count = page.evaluate(
            """
            () => document.querySelectorAll('div.gs_r.gs_or, div.gs_ri, h3.gs_rt').length
            """
        )
        if isinstance(count, int) and count > 0:
            return
    except Exception:
        pass

    if has_block_page(page):
        raise RuntimeError("Possible anti-bot/block page detected")

    raise RuntimeError("No Google Scholar result selectors were detected on the page")


def extract_page_results(page) -> list:
    """Scrape title and year from each result on the currently loaded page."""
    try:
        records = page.evaluate(
            """
            () => {
                const results = [];
                document.querySelectorAll('div.gs_r.gs_or, div.gs_r').forEach(el => {
                    const titleEl = el.querySelector('h3.gs_rt');
                    let title = titleEl ? titleEl.innerText.trim() : '';
                    // Strip leading [PDF], [HTML], [CITATION] markers.
                    title = title.replace(/^\\[.*?\\]\\s*/g, '').trim();

                    const metaEl = el.querySelector('div.gs_a');
                    const metaText = metaEl ? metaEl.innerText : '';
                    const yearMatch = metaText.match(/\\b(19|20)\\d{2}\\b/);
                    const year = yearMatch ? yearMatch[0] : '';

                    if (title) {
                        results.push({ year, title });
                    }
                });
                return results;
            }
            """
        )
        return records if isinstance(records, list) else []
    except Exception as exc:
        print(f"  [warn] Could not extract results from page: {exc}")
        return []


def merge_csv_records(records: list[dict[str, str]], csv_path: Path) -> tuple[int, int]:
    normalized = [
        ("SCHOLA", str(rec.get("year", "") or "????"), str(rec.get("title", "")))
        for rec in records
        if str(rec.get("title", "")).strip()
    ]
    return merge_records_into_csv(csv_path, normalized)


def fetch_openalex_records(
    query: str,
    max_records: int,
    per_page: int,
    timeout_ms: int,
    mailto: str | None,
    log: Callable[[str], None],
) -> list:
    """Fetch TITLE and YEAR from OpenAlex works endpoint."""
    collected: list = []
    cursor = "*"
    page = 0

    while len(collected) < max_records and cursor:
        page += 1
        params = {
            "search": query,
            "per-page": str(per_page),
            "cursor": cursor,
            "select": "display_name,publication_year",
        }
        if mailto:
            params["mailto"] = mailto

        url = f"{OPENALEX_BASE_URL}?{urlencode(params)}"
        req = Request(
            url,
            headers={
                "User-Agent": "DB_Search/1.0 (OpenAlex mode)",
                "Accept": "application/json",
            },
        )

        with urlopen(req, timeout=max(5.0, timeout_ms / 1000.0)) as resp:
            payload = json.loads(resp.read().decode("utf-8"))

        results = payload.get("results", [])
        for item in results:
            title = str(item.get("display_name") or "").strip()
            year = item.get("publication_year")
            if not title:
                continue
            collected.append({"title": title, "year": "" if year is None else str(year)})
            if len(collected) >= max_records:
                break

        meta = payload.get("meta", {})
        cursor = meta.get("next_cursor") or ""
        log(f"  [info] OpenAlex page {page}: +{len(results)} raw, {len(collected)}/{max_records} kept")

        if not results:
            break

    return collected[:max_records]


def save_openalex_results(
    query: str,
    pages: int,
    results_per_page: int,
    csv_path: Path,
    timeout_ms: int,
    mailto: str | None,
    log: Callable[[str], None],
) -> None:
    target = pages * results_per_page
    log(f"Query: {query}")
    log(f"CSV output: {csv_path}")
    log(f"Target via OpenAlex: up to {target} records ({pages} x {results_per_page})")
    if mailto:
        log(f"[info] OpenAlex mailto: {mailto}")

    records = fetch_openalex_records(
        query=query,
        max_records=target,
        per_page=results_per_page,
        timeout_ms=timeout_ms,
        mailto=mailto,
        log=log,
    )
    total_rows, added_rows = merge_csv_records(records, csv_path)
    log(f"[info] Parsed {len(records)} OpenAlex record(s)")
    log(f"[info] CSV now has {total_rows} row(s); added {added_rows}")
    log("[done] OpenAlex collection completed.")


def save_google_scholar_pages_as_pdf(
    query: str,
    pages: int,
    results_per_page: int,
    output_dir: Path,
    csv_path: Path,
    min_delay: float,
    max_delay: float,
    max_retries: int,
    timeout_ms: int,
    headless: bool,
    extract_records: bool,
    settle_min: float,
    settle_max: float,
    scroll_min: float,
    scroll_max: float,
    backoff_min: float,
    backoff_max: float,
    log: Callable[[str], None],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

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

        log(f"Query: {query}")
        log(f"Output dir: {output_dir}")
        log(f"CSV output: {csv_path}")
        log(f"Target: {pages} pages x {results_per_page} results = up to {pages * results_per_page} total")

        all_records: list = []

        for page_idx in range(pages):
            page_number = page_idx + 1
            pdf_file = output_dir / f"P{page_number:02d}.pdf"
            url = build_search_url(query, page_idx, results_per_page)
            success = False

            for attempt in range(1, max_retries + 1):
                try:
                    log(f"  [try {attempt}/{max_retries}] Capturing page {page_number:02d}...")
                    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                    human_wait(settle_min, settle_max)
                    wait_for_results(page, timeout_ms, log)
                    page.mouse.wheel(0, 1600)
                    human_wait(scroll_min, scroll_max)

                    if has_block_page(page):
                        raise RuntimeError("Possible anti-bot/block page detected")

                    if extract_records:
                        page_records = extract_page_results(page)
                        all_records.extend(page_records)
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
                    backoff = random.uniform(backoff_min, backoff_max) * attempt
                    log(f"  [warn] {exc}. Backoff {backoff:.1f}s before retry...")
                    time.sleep(backoff)

            if not success:
                log(f"  [error] Failed page {page_number:02d} after retries")

            human_wait(min_delay, max_delay)

        if extract_records:
            total_rows, added_rows = merge_csv_records(all_records, csv_path)
            log(f"[info] Parsed {len(all_records)} live record(s)")
            log(f"[info] CSV now has {total_rows} row(s); added {added_rows}")
        else:
            log("[info] Download-only mode: CSV extraction skipped.")
        log("[done] Google Scholar page capture completed.")
        context.close()
        browser.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect YEAR/TITLE into GoogleScholar.csv via Scholar scraping or OpenAlex API."
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
        "--source",
        choices=["scholar", "openalex"],
        default=DEFAULT_SOURCE,
        help=f"Data source mode (default: {DEFAULT_SOURCE}).",
    )
    parser.add_argument(
        "--query",
        default=None,
        help="Query string. Defaults to SEARCH_STRING for SS_ID from search-strings CSV.",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=DEFAULT_PAGES,
        help=f"How many result pages to save (default: {DEFAULT_PAGES}).",
    )
    parser.add_argument(
        "--results-per-page",
        type=int,
        default=DEFAULT_RESULTS_PER_PAGE,
        help=(
            f"Results per page (default: {DEFAULT_RESULTS_PER_PAGE}). "
            "Scholar supports 10 or 20; OpenAlex supports 1..200."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory for PDFs (default: src/dataout/SS{SS_ID}/PDF/GoogleScholar).",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Output CSV file for extracted titles/years (default: src/dataout/SS{SS_ID}/GoogleScholar.csv).",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=None,
        help="Directory for run logs (default: src/dataout/SS{SS_ID}/logs/GoogleScholar).",
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
        help="Run browser with GUI.",
    )
    parser.add_argument(
        "--headless",
        dest="headful",
        action="store_false",
        help="Run browser without GUI.",
    )
    parser.set_defaults(headful=True)
    parser.add_argument(
        "--safe",
        action="store_true",
        help="Conservative mode with higher delays and retries.",
    )
    parser.add_argument(
        "--medium",
        action="store_true",
        help="Medium speed mode with moderate delays and retries.",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Faster mode with lower delays and retries (higher anti-bot/block risk).",
    )
    parser.add_argument(
        "--openalex-mailto",
        default=None,
        help="Optional contact email passed to OpenAlex mailto parameter.",
    )
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Download PDFs only and skip live extraction into GoogleScholar.csv.",
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
    output_dir = args.output if args.output is not None else (scope_dir / "PDF" / "GoogleScholar")
    csv_path = args.csv if args.csv is not None else (scope_dir / "GoogleScholar.csv")
    log_dir = args.log_dir if args.log_dir is not None else (scope_dir / "logs" / "GoogleScholar")
    query = args.query.strip() if args.query else scope.search_string.strip()

    if args.source == "scholar" and PLAYWRIGHT_IMPORT_ERROR is not None:
        script_path = Path(__file__).resolve()
        project_python = "/home/jrmgarcia/miniconda3/envs/DB_SEARCH/bin/python"
        print(
            "Playwright is not available in the Python interpreter that launched this script.\n"
            f"Current interpreter: {sys.executable}\n"
            f"Recommended command: {project_python} {script_path} --headful\n"
            "If you want to install it in the current interpreter instead, run:\n"
            f"  {sys.executable} -m pip install playwright\n"
            f"  {sys.executable} -m playwright install chromium",
            file=sys.stderr,
        )
        return 2

    if args.pages < 1:
        print("--pages must be >= 1", file=sys.stderr)
        return 2
    if args.download_only and args.source != "scholar":
        print("--download-only is only valid with --source scholar", file=sys.stderr)
        return 2
    if args.source == "scholar" and args.results_per_page not in (10, 20):
        print("--results-per-page must be 10 or 20 in scholar mode", file=sys.stderr)
        return 2
    if args.source == "openalex" and not (1 <= args.results_per_page <= 200):
        print("--results-per-page must be between 1 and 200 in openalex mode", file=sys.stderr)
        return 2
    if args.min_delay <= 0 or args.max_delay <= 0:
        print("--min-delay and --max-delay must be > 0", file=sys.stderr)
        return 2
    if args.min_delay > args.max_delay:
        print("--min-delay cannot be greater than --max-delay", file=sys.stderr)
        return 2
    if not query:
        print("--query cannot be empty", file=sys.stderr)
        return 2
    selected_profiles = int(args.safe) + int(args.medium) + int(args.fast)
    if selected_profiles > 1:
        print("--safe, --medium, and --fast are mutually exclusive", file=sys.stderr)
        return 2

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"download_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_fh = log_file.open("w", encoding="utf-8")

    def log(message: str) -> None:
        print(message)
        log_fh.write(f"{message}\n")
        log_fh.flush()

    min_delay = args.min_delay
    max_delay = args.max_delay
    max_retries = args.max_retries
    profile_name = DEFAULT_PROFILE
    settle_min = MEDIUM_SETTLE_MIN
    settle_max = MEDIUM_SETTLE_MAX
    scroll_min = MEDIUM_SCROLL_MIN
    scroll_max = MEDIUM_SCROLL_MAX
    backoff_min = MEDIUM_BACKOFF_MIN
    backoff_max = MEDIUM_BACKOFF_MAX

    if args.safe:
        profile_name = "safe"
        min_delay = DEFAULT_MIN_DELAY
        max_delay = DEFAULT_MAX_DELAY
        max_retries = min(max_retries, DEFAULT_MAX_RETRIES)
        settle_min = 2.0
        settle_max = 4.0
        scroll_min = 1.0
        scroll_max = 2.0
        backoff_min = 15.0
        backoff_max = 35.0
    elif args.medium:
        profile_name = "medium"
        min_delay = MEDIUM_MIN_DELAY
        max_delay = MEDIUM_MAX_DELAY
        max_retries = min(max_retries, MEDIUM_MAX_RETRIES)
        settle_min = MEDIUM_SETTLE_MIN
        settle_max = MEDIUM_SETTLE_MAX
        scroll_min = MEDIUM_SCROLL_MIN
        scroll_max = MEDIUM_SCROLL_MAX
        backoff_min = MEDIUM_BACKOFF_MIN
        backoff_max = MEDIUM_BACKOFF_MAX
    elif args.fast:
        profile_name = "fast"
        min_delay = FAST_MIN_DELAY
        max_delay = FAST_MAX_DELAY
        max_retries = min(max_retries, FAST_MAX_RETRIES)
        settle_min = FAST_SETTLE_MIN
        settle_max = FAST_SETTLE_MAX
        scroll_min = FAST_SCROLL_MIN
        scroll_max = FAST_SCROLL_MAX
        backoff_min = FAST_BACKOFF_MIN
        backoff_max = FAST_BACKOFF_MAX

    log(f"[info] Run log: {log_file}")
    log(f"[info] SS_ID: {scope.ss_id}")
    log(f"[info] Search-strings CSV: {scope.config_path}")
    log(f"[info] Source: {args.source}")
    log(f"[info] Extract mode: {'disabled' if args.download_only else 'enabled'}")
    if args.source == "scholar":
        log(f"[info] Profile: {profile_name}")
        log(
            "[info] Timing profile: "
            f"between-pages={min_delay:.1f}-{max_delay:.1f}s, "
            f"settle={settle_min:.1f}-{settle_max:.1f}s, "
            f"scroll={scroll_min:.1f}-{scroll_max:.1f}s, "
            f"retries={max_retries}, "
            f"backoff={backoff_min:.1f}-{backoff_max:.1f}s"
        )

    try:
        if args.source == "openalex":
            save_openalex_results(
                query=query,
                pages=args.pages,
                results_per_page=args.results_per_page,
                csv_path=csv_path,
                timeout_ms=args.timeout_ms,
                mailto=args.openalex_mailto,
                log=log,
            )
        else:
            save_google_scholar_pages_as_pdf(
                query=query,
                pages=args.pages,
                results_per_page=args.results_per_page,
                output_dir=output_dir,
                csv_path=csv_path,
                min_delay=min_delay,
                max_delay=max_delay,
                max_retries=max_retries,
                timeout_ms=args.timeout_ms,
                headless=not args.headful,
                extract_records=not args.download_only,
                settle_min=settle_min,
                settle_max=settle_max,
                scroll_min=scroll_min,
                scroll_max=scroll_max,
                backoff_min=backoff_min,
                backoff_max=backoff_max,
                log=log,
            )
    finally:
        log_fh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())