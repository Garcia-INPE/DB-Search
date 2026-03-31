#!/usr/bin/env python3
"""
Run DB_Search pipeline phases in order.

Default behavior:
- Runs extraction and analysis phases.
- Skips download phase unless --with-download is provided.
- Download phases can build the scoped CSV directly; dedicated PDF re-parse scripts are also available.

Examples:
  python src/99_run_pipeline.py
    python src/99_run_pipeline.py --ss-id 1 --with-download --pages 20
  python src/99_run_pipeline.py --python /home/jrmgarcia/miniconda3/envs/DB_SEARCH/bin/python
    python src/99_run_pipeline.py --with-download --python /home/jrmgarcia/miniconda3/envs/DB_SEARCH/bin/python
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

# Allow interactive execution from terminals not rooted at src/.
SRC_DIR = Path(__file__).resolve().parent if "__file__" in globals() else (Path.cwd() / "src")
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from db_search.search_scope import get_scope_dataout_dir, resolve_search_scope

try:
    sys.stdout.reconfigure(line_buffering=True, write_through=True)
    sys.stderr.reconfigure(line_buffering=True, write_through=True)
except Exception:
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run pipeline scripts in deterministic order."
    )
    parser.add_argument(
        "--with-download",
        action="store_true",
        help="Include phase 01 (Semantic Scholar download).",
    )
    parser.add_argument(
        "--ss-id",
        type=int,
        default=None,
        help="Search-string ID from search-strings CSV. Defaults to the last ID in search-strings CSV.",
    )
    parser.add_argument(
        "--config-csv",
        default=None,
        help="Optional search-strings CSV path (default: src/datain/search_strings.csv; fallback: src/datain/config.csv or src/datain/CSV/config.csv).",
    )
    parser.add_argument(
        "--with-google-download",
        action="store_true",
        help="Include phase 02 (Google collection via script 02; supports OpenAlex mode).",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable for extraction/analysis phases.",
    )
    parser.add_argument(
        "--download-python",
        default=None,
        help="Python executable for download phase (defaults to --python).",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=20,
        help="Number of pages per query for phase 01 (default: 20).",
    )
    parser.add_argument(
        "--google-source",
        choices=["scholar", "openalex"],
        default="openalex",
        help="Source for phase 02 when --with-google-download is set (default: openalex).",
    )
    parser.add_argument(
        "--google-query",
        default=None,
        help="Query forwarded to phase 02 when --with-google-download is set.",
    )
    parser.add_argument(
        "--google-pages",
        type=int,
        default=10,
        help="Number of pages for phase 02 when --with-google-download is set (default: 10).",
    )
    parser.add_argument(
        "--google-results-per-page",
        type=int,
        default=20,
        help="Results per page for phase 02 when --with-google-download is set (default: 20).",
    )
    parser.add_argument(
        "--google-openalex-mailto",
        default=None,
        help="Optional OpenAlex mailto passed to phase 02 when --google-source=openalex.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing.",
    )
    return parser


def run_step(command: List[str], dry_run: bool, expected_outputs: List[str] | None = None) -> Tuple[int, bool]:
    script_name = Path(command[1]).name if len(command) > 1 else Path(command[0]).name
    printable = " ".join(shlex.quote(part) for part in command)
    print(f"[run] {script_name}")

    if dry_run:
        print(f"[cmd] {printable}")
        return 0, False

    has_warning = False
    out_lines: List[str] = []
    ok_lines: List[str] = []
    with subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    ) as proc:
        assert proc.stdout is not None
        for line in proc.stdout:
            stripped = line.strip()
            lowered = stripped.lower()
            if "[warn]" in lowered:
                has_warning = True

            if stripped.startswith("[out]"):
                out_lines.append(stripped)
                continue
            if stripped.startswith("[ok]"):
                ok_lines.append(stripped)
                continue

            print(line, end="")

        returncode = proc.wait()

    if returncode == 0:
        expected = expected_outputs or []
        # Prefer script-reported outputs; fall back to expected outputs when absent.
        output_lines = out_lines if out_lines else [f"[out] {item}" for item in expected]
        for out_line in output_lines:
            print(out_line)

        # Keep one deterministic success marker at the end of each step.
        print(f"[ok] {script_name} completed")

    return returncode, has_warning


def main() -> int:
    args = build_parser().parse_args()

    try:
        scope = resolve_search_scope(args.ss_id, Path(args.config_csv) if args.config_csv else None)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[error] {exc}")
        return 2

    if "__file__" in globals():
        src_dir = Path(__file__).resolve().parent
    else:
        cwd = Path.cwd().resolve()
        start_dir = cwd / "src" if (cwd / "src").is_dir() else cwd
        src_dir = next(
            (p for p in [start_dir, *start_dir.parents] if p.name == "src"),
            start_dir,
        )

    download_python = args.download_python or args.python
    dataout_dir = get_scope_dataout_dir(scope.ss_id)
    charts_dir = dataout_dir / "charts"
    print(f"[info] SS_ID: {scope.ss_id}")
    print(f"[info] Scope dir: {dataout_dir}")

    steps: List[List[str]] = []
    warned_steps: List[str] = []

    if args.with_download:
        download_cmd = [
            download_python,
            str(src_dir / "01_download_semantic_scholar.py"),
            "--ss-id",
            str(scope.ss_id),
            "--pages",
            str(args.pages),
        ]
        steps.append(download_cmd)

    if args.with_google_download:
        google_cmd = [
            download_python,
            str(src_dir / "02_download_google_scholar_pdf.py"),
            "--ss-id",
            str(scope.ss_id),
            "--source",
            args.google_source,
            "--pages",
            str(args.google_pages),
            "--results-per-page",
            str(args.google_results_per_page),
        ]
        if args.google_query:
            google_cmd.extend(["--query", args.google_query])
        if args.google_source == "openalex" and args.google_openalex_mailto:
            google_cmd.extend(["--openalex-mailto", args.google_openalex_mailto])
        steps.append(google_cmd)

    steps.extend(
        [
            [args.python, str(src_dir / "10_extract_csv_bib.py"), "--ss-id", str(scope.ss_id)],
            [args.python, str(src_dir / "30_analyze_papers.py"), "--ss-id", str(scope.ss_id)],
            [args.python, str(src_dir / "31_analyze_db_completeness.py"), "--ss-id", str(scope.ss_id)],
            [args.python, str(src_dir / "32_plot_db_completeness_charts.py"), "--ss-id", str(scope.ss_id)],
        ]
    )

    expected_outputs = {
        "01_download_semantic_scholar.py": [str(dataout_dir / "SemanticScholar.csv")],
        "02_download_google_scholar_pdf.py": [str(dataout_dir / "GoogleScholar.csv")],
        "10_extract_csv_bib.py": [str(dataout_dir / "CSV_and_Bib.csv")],
        "30_analyze_papers.py": [
            str(dataout_dir / "01-TITLES_RAW.csv"),
            str(dataout_dir / "02-TITLES_REVIEW_WF.csv"),
            str(dataout_dir / "02-TITLES_REVIEW_WF_DB_MATRIX.csv"),
            str(dataout_dir / "02-TITLES_REVIEW_WF_DB_MATRIX.html"),
        ],
        "31_analyze_db_completeness.py": [
            str(charts_dir / "db_coverage_from_target.csv"),
            str(charts_dir / "db_from_target_by_year.csv"),
            str(charts_dir / "article_db_match_counts.csv"),
            str(charts_dir / "article_db_match_distribution.csv"),
            str(dataout_dir / "03-UNMATCHED_TITLES.csv"),
        ],
        "32_plot_db_completeness_charts.py": [
            str(charts_dir / "target_articles_found_per_academic_database.png"),
            str(charts_dir / "target_articles_found_per_year_by_academic_database.png"),
            str(charts_dir / "how_many_databases_find_each_target_article.png"),
        ],
    }

# idx = 1; cmd = steps[idx]
    for idx, cmd in enumerate(steps, start=1):
        print(f"\n[step {idx}/{len(steps)}]")
        script_name = Path(cmd[1]).name if len(cmd) > 1 else Path(cmd[0]).name
        code, has_warning = run_step(cmd, args.dry_run, expected_outputs=expected_outputs.get(script_name))
        if code != 0:
            print(f"[error] step failed with exit code {code}")
            return code
        if has_warning:
            warned_steps.append(script_name)
            print(f"[warn] step completed with warnings: {script_name}")

    print("[done] Pipeline completed successfully.")
    if warned_steps:
        print(f"[warn] steps with warnings: {', '.join(warned_steps)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
