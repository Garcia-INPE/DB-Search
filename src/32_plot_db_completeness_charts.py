#!/usr/bin/env python3
"""Create charts from DB completeness analysis outputs.

Expected input files in data directory:
- charts/db_coverage_top12.csv
- charts/db_greedy_cumulative.csv
- charts/year_coverage_gap.csv
- charts/best_db_per_year.csv

Outputs (PNG files) are saved to dataout/charts by default.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch

from db_search.functions import get_db_label


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";", encoding="utf-8")


def ensure_numeric(df: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(df[column], errors="coerce")


def build_db_color_map(db_names: list[str]) -> dict[str, tuple[float, float, float, float]]:
    """Return a deterministic color per DB using a categorical colormap."""
    unique = sorted({str(name) for name in db_names if pd.notna(name) and str(name).strip()})
    cmap = plt.get_cmap("tab20")
    db_colors = {db: cmap(i % 20) for i, db in enumerate(unique)}
    if "SCHOLA" in db_colors:
        db_colors["SCHOLA"] = (0.839, 0.153, 0.157, 1.0)  # fixed highlight red
    return db_colors


def colors_for_dbs(db_series: pd.Series, db_colors: dict[str, tuple[float, float, float, float]]) -> list[tuple[float, float, float, float]]:
    return [db_colors.get(str(db), (0.5, 0.5, 0.5, 1.0)) for db in db_series]


def plot_db_coverage(df: pd.DataFrame, out_path: Path, db_colors: dict[str, tuple[float, float, float, float]]) -> None:
    top = df.sort_values("MATCHED_TITLES", ascending=False).head(12).copy()
    top = top.iloc[::-1]
    top["DB_LABEL"] = top["DB"].astype(str).apply(get_db_label)

    plt.figure(figsize=(10, 6))
    bars = plt.barh(top["DB_LABEL"], top["MATCHED_TITLES"], color=colors_for_dbs(top["DB"], db_colors))
    plt.title("Top Databases by Coverage")
    plt.xlabel("Matched Titles")
    plt.ylabel("Database")
    plt.grid(axis="x", linestyle="--", alpha=0.3)

    for bar, val in zip(bars, top["MATCHED_TITLES"]):
        plt.text(val + 0.2, bar.get_y() + bar.get_height() / 2, f"{int(val)}", va="center", fontsize=9)

    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def plot_greedy(df: pd.DataFrame, out_path: Path, db_colors: dict[str, tuple[float, float, float, float]]) -> None:
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
    ax2.bar(df["STEP"], df["NEW_TITLES_COVERED"], alpha=0.35, color=colors_for_dbs(df["DB"], db_colors))
    ax2.set_ylabel("New Titles Added", color="#ff7f0e")
    ax2.tick_params(axis="y", labelcolor="#ff7f0e")

    labels = [get_db_label(db) for db in df["DB"]]
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


def plot_top_db_by_year(df: pd.DataFrame, out_path: Path, db_colors: dict[str, tuple[float, float, float, float]]) -> None:
    df = df.copy()
    df["YEAR"] = ensure_numeric(df, "YEAR")
    df["MATCHED_TITLES"] = ensure_numeric(df, "MATCHED_TITLES")
    df = df.dropna(subset=["YEAR", "MATCHED_TITLES"])

    idx = df.groupby("YEAR")["MATCHED_TITLES"].idxmax()
    top = df.loc[idx].sort_values("YEAR")

    plt.figure(figsize=(11, 6))
    bars = plt.bar(top["YEAR"].astype(int).astype(str), top["MATCHED_TITLES"], color=colors_for_dbs(top["DB"], db_colors))
    plt.title("Best Single DB by Year")
    plt.xlabel("Year")
    plt.ylabel("Matched Titles")
    plt.grid(axis="y", linestyle="--", alpha=0.25)

    for bar, db in zip(bars, top["DB"]):
        x = bar.get_x() + bar.get_width() / 2
        y = bar.get_height()
        plt.text(x, y + 0.1, get_db_label(db), ha="center", va="bottom", rotation=90, fontsize=8)

    legend_dbs = list(dict.fromkeys(top["DB"].astype(str).tolist()))
    legend_handles = [
        Patch(facecolor=db_colors.get(db, (0.5, 0.5, 0.5, 1.0)), label=get_db_label(db))
        for db in legend_dbs
    ]
    plt.legend(handles=legend_handles, title="DB", fontsize=8, loc="upper left", ncol=2)

    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def plot_direct_db_coverage(df: pd.DataFrame, out_path: Path, db_colors: dict[str, tuple[float, float, float, float]]) -> None:
    """Coverage derived directly from the DB column in the target file (includes SCHOLA)."""
    df = df.copy()
    df["TITLES_INDEXED"] = pd.to_numeric(df["TITLES_INDEXED"], errors="coerce").fillna(0).astype(int)
    df = df.sort_values("TITLES_INDEXED", ascending=True)
    df["DB_LABEL"] = df["DB"].astype(str).apply(get_db_label)

    plt.figure(figsize=(10, 7))
    bars = plt.barh(df["DB_LABEL"], df["TITLES_INDEXED"], color=colors_for_dbs(df["DB"], db_colors))
    plt.title("Titles per Source Database\n(from target file DB tag — includes Google Scholar / SCHOLA)")
    plt.xlabel("Number of Indexed Titles")
    plt.ylabel("Database")
    plt.grid(axis="x", linestyle="--", alpha=0.3)

    for bar, val in zip(bars, df["TITLES_INDEXED"]):
        plt.text(val + 0.2, bar.get_y() + bar.get_height() / 2, f"{int(val)}", va="center", fontsize=9)

    legend_dbs = list(dict.fromkeys(df["DB"].astype(str).tolist()))
    legend_elements = [
        Patch(facecolor=db_colors.get(db, (0.5, 0.5, 0.5, 1.0)), label=get_db_label(db))
        for db in legend_dbs
    ]
    plt.legend(handles=legend_elements, loc="lower right", fontsize=8, ncol=2)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def plot_direct_db_by_year(df: pd.DataFrame, out_path: Path, db_colors: dict[str, tuple[float, float, float, float]]) -> None:
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
    pivot.plot(
        kind="bar",
        stacked=True,
        ax=ax,
        color=[db_colors.get(str(col), (0.5, 0.5, 0.5, 1.0)) for col in pivot.columns],
    )
    ax.set_title("Titles per Year by Source Database\n(from target file DB tag)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Titles Indexed")
    ax.grid(axis="y", linestyle="--", alpha=0.25)
    handles, labels = ax.get_legend_handles_labels()
    labels = [get_db_label(label) for label in labels]
    ax.legend(handles, labels, loc="upper left", fontsize=8, ncol=2)
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

    coverage = read_csv(csv_dir / "db_coverage_top12.csv")
    greedy = read_csv(csv_dir / "db_greedy_cumulative.csv")
    year_summary = read_csv(csv_dir / "year_coverage_gap.csv")
    db_by_year = read_csv(csv_dir / "best_db_per_year.csv")

    direct_cov_path = csv_dir / "db_coverage_from_target.csv"
    direct_year_path = csv_dir / "db_from_target_by_year.csv"
    direct_cov = read_csv(direct_cov_path) if direct_cov_path.is_file() else None
    direct_year = read_csv(direct_year_path) if direct_year_path.is_file() else None

    all_dbs = set(coverage["DB"].astype(str)) | set(greedy["DB"].astype(str)) | set(db_by_year["DB"].astype(str))
    if direct_cov is not None:
        all_dbs |= set(direct_cov["DB"].astype(str))
    if direct_year is not None:
        all_dbs |= set(direct_year["DB"].astype(str))
    db_colors = build_db_color_map(list(all_dbs))

    plot_db_coverage(coverage, out_dir / "db_coverage_top12.png", db_colors)
    plot_greedy(greedy, out_dir / "db_greedy_cumulative.png", db_colors)
    plot_year_summary(year_summary, out_dir / "year_coverage_gap.png")
    plot_top_db_by_year(db_by_year, out_dir / "best_db_per_year.png", db_colors)

    if direct_cov is not None:
        plot_direct_db_coverage(direct_cov, out_dir / "db_coverage_from_target.png", db_colors)
        print(f"[out] {out_dir / 'db_coverage_from_target.png'}")
    if direct_year is not None:
        plot_direct_db_by_year(direct_year, out_dir / "db_from_target_by_year.png", db_colors)
        print(f"[out] {out_dir / 'db_from_target_by_year.png'}")

    print(f"[ok] charts saved to: {out_dir}")
    print(f"[out] {out_dir / 'db_coverage_top12.png'}")
    print(f"[out] {out_dir / 'db_greedy_cumulative.png'}")
    print(f"[out] {out_dir / 'year_coverage_gap.png'}")
    print(f"[out] {out_dir / 'best_db_per_year.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())