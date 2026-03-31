#!/usr/bin/env python3
"""Analyze DB article presence for curated review/survey wildfire titles.

Inputs:
- src/dataout/02-TITLES_REVIEW_WF.csv (target curated list)
- Source database CSV files in src/dataout.

Outputs:
- charts/db_coverage_from_target.csv
- charts/db_from_target_by_year.csv
- charts/article_db_match_counts.csv
- charts/article_db_match_distribution.csv
- src/dataout/03-UNMATCHED_TITLES.csv
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path
from typing import List, Sequence

import pandas as pd

# Allow interactive execution from terminals not rooted at src/.
SRC_DIR = Path(__file__).resolve().parent if "__file__" in globals() else (Path.cwd() / "src")
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from db_search.search_scope import get_scope_dataout_dir, resolve_search_scope


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


def read_target_csv(path: Path) -> pd.DataFrame:
    """Read target CSV (YEAR;TITLE) and return YEAR/TITLE columns."""
    df = pd.read_csv(path, sep=";", encoding="utf-8", dtype=str)
    expected = {"YEAR", "TITLE"}
    if expected.issubset(df.columns):
        out = df[["YEAR", "TITLE"]].copy()
    elif df.shape[1] >= 2:
        out = df.iloc[:, :2].copy()
        out.columns = ["YEAR", "TITLE"]
    else:
        raise ValueError("Target CSV does not have enough columns to map YEAR;TITLE")

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


def build_target_db_matches(target_unique: pd.DataFrame, sources: pd.DataFrame) -> pd.DataFrame:
    """Return one row per (target article, DB) match using normalized titles."""
    source_pairs = (
        sources[["DB", "TITLE_NORM"]]
        .dropna()
        .drop_duplicates()
        .reset_index(drop=True)
    )

    matches = target_unique.merge(source_pairs, on="TITLE_NORM", how="inner")
    if matches.empty:
        return matches

    matches = matches[["TITLE", "YEAR", "YEAR_INT", "TITLE_NORM", "DB"]].drop_duplicates()
    return matches.reset_index(drop=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze DB completeness against curated review/survey wildfire titles.")
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
        "--data-dir",
        default=None,
        help="Directory with input/output CSV files (default: src/dataout/SS{SS_ID}).",
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

    try:
        scope = resolve_search_scope(args.ss_id, args.config_csv)
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(f"[error] {exc}") from exc

    data_dir = Path(args.data_dir).resolve() if args.data_dir else get_scope_dataout_dir(scope.ss_id)
    target_path = data_dir / args.target_file

    print(f"[info] SS_ID: {scope.ss_id}")
    print(f"[info] Scope dir: {data_dir}")

    if not data_dir.is_dir():
        raise SystemExit(f"[error] data directory does not exist: {data_dir}")
    if not target_path.is_file():
        raise SystemExit(f"[error] target CSV not found: {target_path}")

    target = read_target_csv(target_path)
    target = target[target["TITLE"] != ""].copy()
    target["YEAR_INT"] = target["YEAR"].apply(parse_year)
    target["TITLE_NORM"] = target["TITLE"].apply(normalize_title)
    target = target[target["TITLE_NORM"] != ""].copy()

    target_unique = (
        target.sort_values(["TITLE_NORM", "YEAR_INT"], na_position="last")
        .drop_duplicates(subset=["TITLE_NORM"], keep="first")
        .reset_index(drop=True)
    )
    target_unique["YEAR"] = target_unique["YEAR_INT"]
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
    target_db_matches = build_target_db_matches(target_unique, sources)

    total_targets = len(target_unique)

    if target_db_matches.empty:
        coverage_df = pd.DataFrame(columns=["DB", "MATCHED_TITLES", "COVERAGE_PCT"])
        db_year_df = pd.DataFrame(columns=["YEAR", "DB", "MATCHED_TITLES"])
    else:
        coverage_df = (
            target_db_matches.groupby("DB", as_index=False)["TITLE_NORM"]
            .nunique()
            .rename(columns={"TITLE_NORM": "MATCHED_TITLES"})
        )
        coverage_df["COVERAGE_PCT"] = (
            100.0 * coverage_df["MATCHED_TITLES"] / total_targets if total_targets else 0.0
        )
        coverage_df = coverage_df.sort_values(
            ["MATCHED_TITLES", "COVERAGE_PCT", "DB"],
            ascending=[False, False, True],
        ).reset_index(drop=True)

        db_year_df = (
            target_db_matches.groupby(["YEAR", "DB"], dropna=False, as_index=False)["TITLE_NORM"]
            .nunique()
            .rename(columns={"TITLE_NORM": "MATCHED_TITLES"})
            .sort_values(["YEAR", "MATCHED_TITLES", "DB"], ascending=[True, False, True])
            .reset_index(drop=True)
        )

    matched_title_set = set(target_db_matches["TITLE_NORM"].astype(str)) if not target_db_matches.empty else set()
    target_with_any = target_unique.copy()
    target_with_any["FOUND_IN_ANY_DB"] = target_with_any["TITLE_NORM"].isin(matched_title_set)

    unmatched = target_unique[~target_with_any["FOUND_IN_ANY_DB"]].copy()
    unmatched = unmatched[["YEAR", "TITLE"]] if "YEAR" in unmatched.columns else unmatched[["TITLE"]]

    if target_db_matches.empty:
        article_db_counts = pd.DataFrame(columns=["YEAR", "TITLE", "DB_COUNT"])
        article_db_distribution = pd.DataFrame(columns=["DB_COUNT", "ARTICLE_COUNT"])
    else:
        article_db_counts = (
            target_db_matches.groupby(["TITLE_NORM", "TITLE", "YEAR"], as_index=False)["DB"]
            .nunique()
            .rename(columns={"DB": "DB_COUNT"})
            .sort_values(["DB_COUNT", "YEAR", "TITLE"], ascending=[False, True, True])
            .reset_index(drop=True)
        )

        article_db_distribution = (
            article_db_counts.groupby("DB_COUNT", as_index=False)
            .size()
            .rename(columns={"size": "ARTICLE_COUNT"})
            .sort_values("DB_COUNT")
            .reset_index(drop=True)
        )

    # --- Coverage per DB: how many target articles each DB found across ALL sources ----------
    # Derived from the source-based match (coverage_df / db_year_df) so every DB that
    # indexed a target article is counted, regardless of which DB "won" deduplication.
    direct_cov = (
        coverage_df[["DB", "MATCHED_TITLES", "COVERAGE_PCT"]]
        .rename(columns={"MATCHED_TITLES": "TARGET_ARTICLES_FOUND"})
        .sort_values(["TARGET_ARTICLES_FOUND", "DB"], ascending=[False, True])
        .reset_index(drop=True)
    )

    # Per-year articles per DB: same source-based logic, each article counted once per DB
    direct_by_year = (
        db_year_df[["YEAR", "DB", "MATCHED_TITLES"]]
        .rename(columns={"MATCHED_TITLES": "TARGET_ARTICLES_FOUND"})
        .sort_values(["YEAR", "TARGET_ARTICLES_FOUND", "DB"], ascending=[True, False, True])
        .reset_index(drop=True)
    )

    charts_dir = data_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    unmatched_path = data_dir / "03-UNMATCHED_TITLES.csv"
    direct_cov_path = charts_dir / "db_coverage_from_target.csv"
    direct_by_year_path = charts_dir / "db_from_target_by_year.csv"
    article_db_counts_path = charts_dir / "article_db_match_counts.csv"
    article_db_distribution_path = charts_dir / "article_db_match_distribution.csv"

    unmatched.to_csv(unmatched_path, sep=";", index=False, encoding="utf-8")
    direct_cov.to_csv(direct_cov_path, sep=";", index=False, encoding="utf-8")
    direct_by_year.to_csv(direct_by_year_path, sep=";", index=False, encoding="utf-8")
    article_db_counts[["YEAR", "TITLE", "DB_COUNT"]].to_csv(
        article_db_counts_path,
        sep=";",
        index=False,
        encoding="utf-8",
    )
    article_db_distribution.to_csv(article_db_distribution_path, sep=";", index=False, encoding="utf-8")

    top_direct = direct_cov.iloc[0]["DB"] if len(direct_cov) else "N/A"
    top_direct_n = direct_cov.iloc[0]["TARGET_ARTICLES_FOUND"] if len(direct_cov) else 0

    print(f"[ok] target titles (unique normalized): {total_targets}")
    print(f"[ok] source files used: {len(source_files) - len(skipped_files)}")
    if skipped_files:
        print(f"[warn] skipped files (schema/read issues): {', '.join(sorted(skipped_files))}")
    print(f"[ok] top DB by target-article matches: {top_direct} ({top_direct_n} titles)")
    print(f"[out] {unmatched_path}")
    print(f"[out] {direct_cov_path}")
    print(f"[out] {direct_by_year_path}")
    print(f"[out] {article_db_counts_path}")
    print(f"[out] {article_db_distribution_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())