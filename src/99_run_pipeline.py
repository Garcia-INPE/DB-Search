#!/usr/bin/env python3
"""
Run DB_Search pipeline phases in order.

Default behavior:
- Runs extraction and analysis phases.
- Skips download phase unless --with-download is provided.

Examples:
  python src/99_run_pipeline.py
  python src/99_run_pipeline.py --with-download --queries-file queries.txt --pages 20
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
        "--queries",
        nargs="*",
        default=[],
        help="Query strings forwarded to phase 01 when --with-download is set.",
    )
    parser.add_argument(
        "--queries-file",
        default=None,
        help="Queries file forwarded to phase 01 when --with-download is set.",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=20,
        help="Number of pages per query for phase 01 (default: 20).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing.",
    )
    return parser


def run_step(command: List[str], dry_run: bool) -> Tuple[int, bool]:
    printable = " ".join(shlex.quote(part) for part in command)
    print(f"\n[run] {printable}")

    if dry_run:
        return 0, False

    completed = subprocess.run(command, capture_output=True, text=True)

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)

    combined_output = "\n".join(part for part in [stdout, stderr] if part)
    has_warning = "[warn]" in combined_output.lower()
    return completed.returncode, has_warning


def main() -> int:
    args = build_parser().parse_args()

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

    steps: List[List[str]] = []
    warned_steps: List[str] = []

    if args.with_download:
        download_cmd = [
            download_python,
            str(src_dir / "01_download_semantic_scholar.py"),
            "--pages",
            str(args.pages),
        ]
        if args.queries:
            download_cmd.append("--queries")
            download_cmd.extend(args.queries)
        elif args.queries_file:
            download_cmd.extend(["--queries-file", args.queries_file])
        steps.append(download_cmd)

    steps.extend(
        [
            [args.python, str(src_dir / "10_extract_csv_bib.py")],
            [args.python, str(src_dir / "11_extract_pdf_google_scholar.py")],
            [args.python, str(src_dir / "14_extract_pdf_semantic_scholar.py")],
            [args.python, str(src_dir / "30_analyze_papers.py")],
            [args.python, str(src_dir / "31_analyze_db_completeness.py")],
            [args.python, str(src_dir / "32_plot_db_completeness_charts.py")],
        ]
    )

# idx = 1; cmd = steps[idx]
    for idx, cmd in enumerate(steps, start=1):
        print(f"[step {idx}/{len(steps)}]")
        code, has_warning = run_step(cmd, args.dry_run)
        if code != 0:
            print(f"[error] step failed with exit code {code}")
            return code
        if has_warning:
            warned_steps.append(Path(cmd[1]).name)
            print(f"[warn] step completed with warnings: {Path(cmd[1]).name}")

    print("\n[done] Pipeline completed successfully.")
    if warned_steps:
        print(f"[warn] steps with warnings: {', '.join(warned_steps)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
