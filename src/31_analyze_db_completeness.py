#!/usr/bin/env python3
"""Analyze DB completeness for curated review/survey wildfire titles.

Inputs:
- src/dataout/02-TITLES_REVIEW_WF.csv (target curated list)
- Source database CSV files in src/dataout.

Outputs:
- charts/db_coverage_top12.csv
- charts/db_greedy_cumulative.csv
- charts/year_coverage_gap.csv
- charts/best_db_per_year.csv
- charts/db_coverage_from_target.csv
- charts/db_from_target_by_year.csv
- src/dataout/03-UNMATCHED_TITLES.csv
"""

from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

import pandas as pd


def normalize_title(text: str) -> str:
    """Normalize titles for robust exact matching across CSVs."""
    text = "" if text is None else str(text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    # Remove apostrophes so daxing'anling/children's/likelihood's align with de-quoted variants.
    text = re.sub(r"['’`´]", "", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_year(value: object) -> int | None:
    """Extract a 4-digit year; return None when unavailable/invalid."""
    if value is None:
        return None
    txt = str(value).strip()
    match = re.search(r"(19\d{2}|20\d{2}|2100)", txt)
    if not match:
        return None
    return int(match.group(1))


def read_semicolon_csv(path: Path) -> pd.DataFrame:
    """Read a ; separated CSV and standardize expected columns."""
    df = pd.read_csv(path, sep=";", encoding="utf-8", dtype=str)

    expected = {"DB", "YEAR", "TITLE"}
    if expected.issubset(df.columns):
        out = df[["DB", "YEAR", "TITLE"]].copy()
    elif df.shape[1] >= 3:
        out = df.iloc[:, :3].copy()
        out.columns = ["DB", "YEAR", "TITLE"]
    else:
        raise ValueError("CSV does not have enough columns to map DB;YEAR;TITLE")

    out["DB"] = out["DB"].fillna("").astype(str).str.strip()
    out["YEAR"] = out["YEAR"].fillna("").astype(str).str.strip()
    out["TITLE"] = out["TITLE"].fillna("").astype(str).str.strip()
    return out


def collect_source_files(data_dir: Path, excludes: Sequence[str]) -> List[Path]:
    """Return only raw source database CSV files used by the pipeline."""
    excluded = {name.lower() for name in excludes}
    source_names = ["CSV_and_Bib.csv", "GoogleScholar.csv", "SemanticScholar.csv"]

    files: List[Path] = []
    for name in source_names:
        path = data_dir / name
        if not path.is_file():
            continue
        if path.name.lower() in excluded:
            continue
        files.append(path)
    return files


def build_db_title_index(sources: pd.DataFrame) -> Dict[str, Set[str]]:
    """Map DB -> normalized title set."""
    db_to_titles: Dict[str, Set[str]] = {}
    for db, group in sources.groupby("DB"):
        db_clean = str(db).strip()
        if not db_clean:
            continue
        title_set = set(group["TITLE_NORM"].dropna().astype(str))
        title_set.discard("")
        if title_set:
            db_to_titles[db_clean] = title_set
    return db_to_titles


def greedy_db_order(db_to_titles: Dict[str, Set[str]], target_titles: Set[str]) -> List[Tuple[int, str, int, int, float]]:
    """Greedy ranking: each step picks DB adding most uncovered target titles."""
    covered: Set[str] = set()
    remaining_dbs = set(db_to_titles)
    out: List[Tuple[int, str, int, int, float]] = []
    step = 1
    total_targets = len(target_titles)

    while remaining_dbs:
        best_db = None
        best_new = set()

        for db in remaining_dbs:
            new_titles = (db_to_titles[db] & target_titles) - covered
            if len(new_titles) > len(best_new):
                best_db = db
                best_new = new_titles

        if best_db is None:
            break

        covered |= best_new
        cumulative = len(covered)
        cumulative_pct = (100.0 * cumulative / total_targets) if total_targets else 0.0
        out.append((step, best_db, len(best_new), cumulative, cumulative_pct))

        remaining_dbs.remove(best_db)
        step += 1

        if cumulative == total_targets:
            break

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze DB completeness against curated review/survey wildfire titles.")
    parser.add_argument(
        "--data-dir",
        default=str(Path(__file__).resolve().parent / "dataout"),
        help="Directory with input/output CSV files (default: src/dataout).",
    )
    parser.add_argument(
        "--target-file",
        default="02-TITLES_REVIEW_WF.csv",
        help="Target CSV filename inside --data-dir.",
    )
    parser.add_argument(
        "--exclude-files",
        nargs="*",
        default=[],
        help="Extra CSV filenames to ignore from sources (numbered output files are always excluded).",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir).resolve()
    target_path = data_dir / args.target_file

    if not data_dir.is_dir():
        raise SystemExit(f"[error] data directory does not exist: {data_dir}")
    if not target_path.is_file():
        raise SystemExit(f"[error] target CSV not found: {target_path}")

    target = read_semicolon_csv(target_path)
    target = target[target["TITLE"] != ""].copy()
    target["YEAR_INT"] = target["YEAR"].apply(parse_year)
    target["TITLE_NORM"] = target["TITLE"].apply(normalize_title)
    target = target[target["TITLE_NORM"] != ""].copy()

    target_unique = (
        target.sort_values(["TITLE_NORM", "YEAR_INT"], na_position="last")
        .drop_duplicates(subset=["TITLE_NORM"], keep="first")
        .reset_index(drop=True)
    )
    target_titles_set = set(target_unique["TITLE_NORM"])

    source_files = collect_source_files(data_dir, args.exclude_files)
    # Never include the target file itself as a source DB.
    source_files = [p for p in source_files if p.name != target_path.name]
    if not source_files:
        raise SystemExit("[error] no source CSV files found after exclusions")

    source_frames: List[pd.DataFrame] = []
    skipped_files: List[str] = []
    for csv_path in source_files:
        try:
            df = read_semicolon_csv(csv_path)
        except Exception:
            skipped_files.append(csv_path.name)
            continue
        df = df[df["TITLE"] != ""].copy()
        df["YEAR_INT"] = df["YEAR"].apply(parse_year)
        df["TITLE_NORM"] = df["TITLE"].apply(normalize_title)
        df = df[df["TITLE_NORM"] != ""].copy()
        source_frames.append(df)

    if not source_frames:
        raise SystemExit("[error] all source CSV files were skipped or empty")

    sources = pd.concat(source_frames, ignore_index=True)
    db_to_titles = build_db_title_index(sources)

    total_targets = len(target_unique)

    coverage_rows = []
    for db, title_set in sorted(db_to_titles.items()):
        matched = len(title_set & target_titles_set)
        pct = (100.0 * matched / total_targets) if total_targets else 0.0
        coverage_rows.append((db, matched, pct))

    coverage_df = pd.DataFrame(coverage_rows, columns=["DB", "MATCHED_TITLES", "COVERAGE_PCT"])
    coverage_df = coverage_df.sort_values(["MATCHED_TITLES", "COVERAGE_PCT", "DB"], ascending=[False, False, True]).reset_index(drop=True)

    greedy_rows = greedy_db_order(db_to_titles, target_titles_set)
    greedy_df = pd.DataFrame(
        greedy_rows,
        columns=["STEP", "DB", "NEW_TITLES_COVERED", "CUMULATIVE_COVERED", "CUMULATIVE_PCT"],
    )

    target_with_any = target_unique.copy()
    all_source_titles = set(sources["TITLE_NORM"].astype(str))
    target_with_any["FOUND_IN_ANY_DB"] = target_with_any["TITLE_NORM"].isin(all_source_titles)

    year_summary = (
        target_with_any.groupby("YEAR_INT", dropna=False)
        .agg(
            TARGET_TITLES=("TITLE_NORM", "count"),
            FOUND_IN_ANY_DB=("FOUND_IN_ANY_DB", "sum"),
        )
        .reset_index()
    )
    year_summary["MISSING_IN_ANY_DB"] = year_summary["TARGET_TITLES"] - year_summary["FOUND_IN_ANY_DB"]
    year_summary = year_summary.rename(columns={"YEAR_INT": "YEAR"})
    year_summary = year_summary.sort_values("YEAR", na_position="last").reset_index(drop=True)

    db_year_rows = []
    for db, title_set in sorted(db_to_titles.items()):
        matched_mask = target_unique["TITLE_NORM"].isin(title_set)
        db_year = (
            target_unique.loc[matched_mask]
            .groupby("YEAR_INT", dropna=False)
            .size()
            .reset_index(name="MATCHED_TITLES")
        )
        db_year["DB"] = db
        db_year_rows.append(db_year)

    if db_year_rows:
        db_year_df = pd.concat(db_year_rows, ignore_index=True)
        db_year_df = db_year_df.rename(columns={"YEAR_INT": "YEAR"})
        db_year_df = db_year_df[["YEAR", "DB", "MATCHED_TITLES"]]
        db_year_df = db_year_df.sort_values(["YEAR", "MATCHED_TITLES", "DB"], ascending=[True, False, True]).reset_index(drop=True)
    else:
        db_year_df = pd.DataFrame(columns=["YEAR", "DB", "MATCHED_TITLES"])

    unmatched = target_unique[~target_with_any["FOUND_IN_ANY_DB"]].copy()
    unmatched = unmatched[["YEAR", "TITLE"]] if "YEAR" in unmatched.columns else unmatched[["TITLE"]]

    # --- Direct coverage from the DB column in the target file itself ----------
    # This includes SCHOLA (Google Scholar) and any DB not present in source CSV files.
    direct_cov = (
        target_unique.groupby("DB")
        .agg(TITLES_INDEXED=("TITLE_NORM", "count"))
        .reset_index()
    )
    direct_cov["COVERAGE_PCT"] = (100.0 * direct_cov["TITLES_INDEXED"] / total_targets) if total_targets else 0.0
    direct_cov = direct_cov.sort_values(["TITLES_INDEXED", "DB"], ascending=[False, True]).reset_index(drop=True)

    # Per-year breakdown by DB directly from target file
    direct_by_year = (
        target_unique.groupby(["YEAR_INT", "DB"])
        .size()
        .reset_index(name="TITLES_INDEXED")
        .rename(columns={"YEAR_INT": "YEAR"})
    )
    direct_by_year = direct_by_year.sort_values(["YEAR", "TITLES_INDEXED", "DB"], ascending=[True, False, True]).reset_index(drop=True)

    charts_dir = data_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    coverage_path = charts_dir / "db_coverage_top12.csv"
    greedy_path = charts_dir / "db_greedy_cumulative.csv"
    year_path = charts_dir / "year_coverage_gap.csv"
    db_year_path = charts_dir / "best_db_per_year.csv"
    unmatched_path = data_dir / "03-UNMATCHED_TITLES.csv"
    direct_cov_path = charts_dir / "db_coverage_from_target.csv"
    direct_by_year_path = charts_dir / "db_from_target_by_year.csv"

    coverage_df.to_csv(coverage_path, sep=";", index=False, encoding="utf-8")
    greedy_df.to_csv(greedy_path, sep=";", index=False, encoding="utf-8")
    year_summary.to_csv(year_path, sep=";", index=False, encoding="utf-8")
    db_year_df.to_csv(db_year_path, sep=";", index=False, encoding="utf-8")
    unmatched.to_csv(unmatched_path, sep=";", index=False, encoding="utf-8")
    direct_cov.to_csv(direct_cov_path, sep=";", index=False, encoding="utf-8")
    direct_by_year.to_csv(direct_by_year_path, sep=";", index=False, encoding="utf-8")

    top_db = coverage_df.iloc[0]["DB"] if len(coverage_df) else "N/A"
    top_cov = coverage_df.iloc[0]["MATCHED_TITLES"] if len(coverage_df) else 0
    top_direct = direct_cov.iloc[0]["DB"] if len(direct_cov) else "N/A"
    top_direct_n = direct_cov.iloc[0]["TITLES_INDEXED"] if len(direct_cov) else 0

    print(f"[ok] target titles (unique normalized): {total_targets}")
    print(f"[ok] source files used: {len(source_files) - len(skipped_files)}")
    if skipped_files:
        print(f"[warn] skipped files (schema/read issues): {', '.join(sorted(skipped_files))}")
    print(f"[ok] top DB by title-match in sources: {top_db} ({top_cov} titles)")
    print(f"[ok] top DB by direct indexing (target file): {top_direct} ({top_direct_n} titles)")
    print(f"[out] {coverage_path}")
    print(f"[out] {greedy_path}")
    print(f"[out] {year_path}")
    print(f"[out] {db_year_path}")
    print(f"[out] {unmatched_path}")
    print(f"[out] {direct_cov_path}")
    print(f"[out] {direct_by_year_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())