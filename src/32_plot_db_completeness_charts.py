#!/usr/bin/env python3
"""Create charts from DB completeness analysis outputs.

Expected input files in data directory:
- charts/DB_COVERAGE_SUMMARY.csv
- charts/DB_GREEDY_ORDER.csv
- charts/YEAR_SUMMARY.csv
- charts/DB_BY_YEAR.csv

Outputs (PNG files) are saved to dataout/charts by default.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";", encoding="utf-8")


def ensure_numeric(df: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(df[column], errors="coerce")


def plot_db_coverage(df: pd.DataFrame, out_path: Path) -> None:
    top = df.sort_values("MATCHED_TITLES", ascending=False).head(12).copy()
    top = top.iloc[::-1]

    plt.figure(figsize=(10, 6))
    bars = plt.barh(top["DB"], top["MATCHED_TITLES"], color="#1f77b4")
    plt.title("Top Databases by Matched Titles")
    plt.xlabel("Matched Titles")
    plt.ylabel("Database")
    plt.grid(axis="x", linestyle="--", alpha=0.3)

    for bar, val in zip(bars, top["MATCHED_TITLES"]):
        plt.text(val + 0.2, bar.get_y() + bar.get_height() / 2, f"{int(val)}", va="center", fontsize=9)

    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def plot_greedy(df: pd.DataFrame, out_path: Path) -> None:
    df = df.copy()
    df["STEP"] = ensure_numeric(df, "STEP")
    df["CUMULATIVE_PCT"] = ensure_numeric(df, "CUMULATIVE_PCT")
    df["NEW_TITLES_COVERED"] = ensure_numeric(df, "NEW_TITLES_COVERED")

    fig, ax1 = plt.subplots(figsize=(10, 6))

    ax1.plot(df["STEP"], df["CUMULATIVE_PCT"], marker="o", color="#2ca02c", linewidth=2)
    ax1.set_xlabel("Step")
    ax1.set_ylabel("Cumulative Coverage (%)", color="#2ca02c")
    ax1.tick_params(axis="y", labelcolor="#2ca02c")
    ax1.set_ylim(0, 100)
    ax1.grid(axis="both", linestyle="--", alpha=0.25)

    ax2 = ax1.twinx()
    ax2.bar(df["STEP"], df["NEW_TITLES_COVERED"], alpha=0.25, color="#ff7f0e")
    ax2.set_ylabel("New Titles Added", color="#ff7f0e")
    ax2.tick_params(axis="y", labelcolor="#ff7f0e")

    labels = [f"{db}" for db in df["DB"]]
    ax1.set_xticks(df["STEP"])
    ax1.set_xticklabels(labels, rotation=45, ha="right")

    plt.title("Greedy DB Order: Cumulative Coverage and Incremental Gain")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def plot_year_summary(df: pd.DataFrame, out_path: Path) -> None:
    df = df.copy()
    df["YEAR"] = ensure_numeric(df, "YEAR")
    df["TARGET_TITLES"] = ensure_numeric(df, "TARGET_TITLES")
    df["FOUND_IN_ANY_DB"] = ensure_numeric(df, "FOUND_IN_ANY_DB")
    df = df.dropna(subset=["YEAR"])
    df = df.sort_values("YEAR")

    plt.figure(figsize=(11, 6))
    plt.plot(df["YEAR"], df["TARGET_TITLES"], marker="o", linewidth=2, label="Target Titles")
    plt.plot(df["YEAR"], df["FOUND_IN_ANY_DB"], marker="o", linewidth=2, label="Found in Sources")
    plt.fill_between(df["YEAR"], df["FOUND_IN_ANY_DB"], df["TARGET_TITLES"], alpha=0.15, label="Gap")
    plt.title("Coverage by Publication Year")
    plt.xlabel("Year")
    plt.ylabel("Count of Titles")
    plt.grid(linestyle="--", alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def plot_top_db_by_year(df: pd.DataFrame, out_path: Path) -> None:
    df = df.copy()
    df["YEAR"] = ensure_numeric(df, "YEAR")
    df["MATCHED_TITLES"] = ensure_numeric(df, "MATCHED_TITLES")
    df = df.dropna(subset=["YEAR", "MATCHED_TITLES"])

    idx = df.groupby("YEAR")["MATCHED_TITLES"].idxmax()
    top = df.loc[idx].sort_values("YEAR")

    plt.figure(figsize=(11, 6))
    bars = plt.bar(top["YEAR"].astype(int).astype(str), top["MATCHED_TITLES"], color="#9467bd")
    plt.title("Best Single DB by Year (Matched Titles)")
    plt.xlabel("Year")
    plt.ylabel("Matched Titles")
    plt.grid(axis="y", linestyle="--", alpha=0.25)

    for bar, db in zip(bars, top["DB"]):
        x = bar.get_x() + bar.get_width() / 2
        y = bar.get_height()
        plt.text(x, y + 0.1, str(db), ha="center", va="bottom", rotation=90, fontsize=8)

    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def plot_direct_db_coverage(df: pd.DataFrame, out_path: Path) -> None:
    """Coverage derived directly from the DB column in the target file (includes SCHOLA)."""
    df = df.copy()
    df["TITLES_INDEXED"] = pd.to_numeric(df["TITLES_INDEXED"], errors="coerce").fillna(0).astype(int)
    df = df.sort_values("TITLES_INDEXED", ascending=True)

    # Color SCHOLA differently so it stands out
    colors = ["#d62728" if db == "SCHOLA" else "#1f77b4" for db in df["DB"]]

    plt.figure(figsize=(10, 7))
    bars = plt.barh(df["DB"], df["TITLES_INDEXED"], color=colors)
    plt.title("Titles per Source Database\n(from target file DB tag — includes Google Scholar / SCHOLA)")
    plt.xlabel("Number of Indexed Titles")
    plt.ylabel("Database")
    plt.grid(axis="x", linestyle="--", alpha=0.3)

    for bar, val in zip(bars, df["TITLES_INDEXED"]):
        plt.text(val + 0.2, bar.get_y() + bar.get_height() / 2, f"{int(val)}", va="center", fontsize=9)

    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#d62728", label="Google Scholar (SCHOLA)"),
        Patch(facecolor="#1f77b4", label="Other databases"),
    ]
    plt.legend(handles=legend_elements, loc="lower right")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def plot_direct_db_by_year(df: pd.DataFrame, out_path: Path) -> None:
    """Stacked bar per year, broken down by which DB indexed each title."""
    df = df.copy()
    df["YEAR"] = pd.to_numeric(df["YEAR"], errors="coerce")
    df["TITLES_INDEXED"] = pd.to_numeric(df["TITLES_INDEXED"], errors="coerce").fillna(0)
    df = df.dropna(subset=["YEAR"])
    df["YEAR"] = df["YEAR"].astype(int)

    pivot = df.pivot_table(index="YEAR", columns="DB", values="TITLES_INDEXED", aggfunc="sum", fill_value=0)
    # Move SCHOLA to first column so it gets a prominent color
    if "SCHOLA" in pivot.columns:
        cols = ["SCHOLA"] + [c for c in pivot.columns if c != "SCHOLA"]
        pivot = pivot[cols]

    fig, ax = plt.subplots(figsize=(13, 6))
    pivot.plot(kind="bar", stacked=True, ax=ax, colormap="tab20")
    ax.set_title("Titles per Year by Source Database\n(from target file DB tag)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Titles Indexed")
    ax.grid(axis="y", linestyle="--", alpha=0.25)
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate charts from DB completeness CSV outputs.")
    parser.add_argument(
        "--data-dir",
        default=str(Path(__file__).resolve().parent / "dataout"),
        help="Directory containing analysis CSV files.",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Output directory for chart PNG files (default: <data-dir>/charts).",
    )
    parser.add_argument(
        "--csv-dir",
        default=None,
        help="Directory containing chart input CSV files (default: <data-dir>/charts).",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir).resolve()
    out_dir = Path(args.out_dir).resolve() if args.out_dir else (data_dir / "charts")
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_dir = Path(args.csv_dir).resolve() if args.csv_dir else out_dir

    coverage = read_csv(csv_dir / "DB_COVERAGE_SUMMARY.csv")
    greedy = read_csv(csv_dir / "DB_GREEDY_ORDER.csv")
    year_summary = read_csv(csv_dir / "YEAR_SUMMARY.csv")
    db_by_year = read_csv(csv_dir / "DB_BY_YEAR.csv")

    plot_db_coverage(coverage, out_dir / "db_coverage_top12.png")
    plot_greedy(greedy, out_dir / "db_greedy_cumulative.png")
    plot_year_summary(year_summary, out_dir / "year_coverage_gap.png")
    plot_top_db_by_year(db_by_year, out_dir / "best_db_per_year.png")

    direct_cov_path = csv_dir / "DB_COVERAGE_FROM_TARGET.csv"
    direct_year_path = csv_dir / "DB_FROM_TARGET_BY_YEAR.csv"
    if direct_cov_path.is_file():
        direct_cov = read_csv(direct_cov_path)
        plot_direct_db_coverage(direct_cov, out_dir / "db_coverage_from_target.png")
        print(f"[out] {out_dir / 'db_coverage_from_target.png'}")
    if direct_year_path.is_file():
        direct_year = read_csv(direct_year_path)
        plot_direct_db_by_year(direct_year, out_dir / "db_from_target_by_year.png")
        print(f"[out] {out_dir / 'db_from_target_by_year.png'}")

    print(f"[ok] charts saved to: {out_dir}")
    print(f"[out] {out_dir / 'db_coverage_top12.png'}")
    print(f"[out] {out_dir / 'db_greedy_cumulative.png'}")
    print(f"[out] {out_dir / 'year_coverage_gap.png'}")
    print(f"[out] {out_dir / 'best_db_per_year.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())