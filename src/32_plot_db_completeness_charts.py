#!/usr/bin/env python3
"""Create charts from target-article DB match analysis outputs.

Expected input files in data directory:
- charts/db_coverage_from_target.csv
- charts/db_from_target_by_year.csv
- charts/article_db_match_distribution.csv

Outputs (PNG files) are saved to dataout/charts by default.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator

# Allow interactive execution from terminals not rooted at src/.
SRC_DIR = Path(__file__).resolve().parent if "__file__" in globals() else (Path.cwd() / "src")
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from db_search.functions import get_db_label
from db_search.search_scope import get_scope_dataout_dir, resolve_search_scope


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";", encoding="utf-8")


def ensure_numeric(df: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(df[column], errors="coerce")


def slugify_title(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return f"{slug}.png"


def annotate_line_points(ax, x_values, y_values, formatter=str, y_offset: float = 0.8) -> None:
    for x_val, y_val in zip(x_values, y_values):
        if pd.isna(x_val) or pd.isna(y_val):
            continue
        ax.text(x_val, y_val + y_offset, formatter(y_val), ha="center", va="bottom", fontsize=8)


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


def plot_db_coverage(df: pd.DataFrame, out_path: Path, db_colors: dict[str, tuple[float, float, float, float]]) -> str:
    top = df.sort_values("MATCHED_TITLES", ascending=False).head(12).copy()
    top["MATCHED_TITLES"] = ensure_numeric(top, "MATCHED_TITLES").fillna(0).astype(int)
    top = top.iloc[::-1]
    top["DB_LABEL"] = top["DB"].astype(str).apply(get_db_label)
    title = "Top Academic Databases by Coverage"

    plt.figure(figsize=(10, 6))
    bars = plt.barh(top["DB_LABEL"], top["MATCHED_TITLES"], color=colors_for_dbs(top["DB"], db_colors))
    plt.title(title)
    plt.xlabel("Number of Articles")
    plt.ylabel("Academic Database")
    plt.grid(axis="x", linestyle="--", alpha=0.3)
    plt.gca().xaxis.set_major_locator(MaxNLocator(integer=True))

    for bar, val in zip(bars, top["MATCHED_TITLES"]):
        plt.text(val + 0.2, bar.get_y() + bar.get_height() / 2, f"{int(val)}", va="center", fontsize=9)

    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    return title


def plot_greedy(df: pd.DataFrame, out_path: Path, db_colors: dict[str, tuple[float, float, float, float]]) -> str:
    df = df.copy()
    df["STEP"] = ensure_numeric(df, "STEP").fillna(0).astype(int)
    df["CUMULATIVE_PCT"] = ensure_numeric(df, "CUMULATIVE_PCT")
    df["NEW_TITLES_COVERED"] = ensure_numeric(df, "NEW_TITLES_COVERED").fillna(0).astype(int)
    title = "Cumulative Coverage by Academic Database Order"

    fig, ax1 = plt.subplots(figsize=(10, 6))

    ax1.plot(df["STEP"], df["CUMULATIVE_PCT"], marker="o", color="#2ca02c", linewidth=2)
    ax1.set_xlabel("")
    ax1.set_ylabel("Cumulative Coverage (%)", color="#2ca02c")
    ax1.tick_params(axis="y", labelcolor="#2ca02c")
    ax1.set_ylim(0, 100)
    ax1.grid(axis="both", linestyle="--", alpha=0.25)
    annotate_line_points(ax1, df["STEP"], df["CUMULATIVE_PCT"], formatter=lambda value: f"{int(round(value))}%", y_offset=1.2)

    ax2 = ax1.twinx()
    ax2.bar(df["STEP"], df["NEW_TITLES_COVERED"], alpha=0.35, color=colors_for_dbs(df["DB"], db_colors))
    ax2.set_ylabel("Number of Articles Added", color="#ff7f0e")
    ax2.tick_params(axis="y", labelcolor="#ff7f0e")
    ax2.yaxis.set_major_locator(MaxNLocator(integer=True))

    labels = [get_db_label(db) for db in df["DB"]]
    ax1.set_xticks(df["STEP"])
    ax1.set_xticklabels(labels, rotation=45, ha="right")

    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    return title


def plot_year_summary(df: pd.DataFrame, out_path: Path) -> str:
    df = df.copy()
    df["YEAR"] = ensure_numeric(df, "YEAR")
    df["TARGET_TITLES"] = ensure_numeric(df, "TARGET_TITLES").fillna(0).astype(int)
    df["FOUND_IN_ANY_DB"] = ensure_numeric(df, "FOUND_IN_ANY_DB").fillna(0).astype(int)
    df = df.dropna(subset=["YEAR"])
    df["YEAR"] = df["YEAR"].astype(int)
    df = df.sort_values("YEAR")
    title = "Article Coverage by Publication Year"

    plt.figure(figsize=(11, 6))
    ax = plt.gca()
    ax.plot(df["YEAR"], df["FOUND_IN_ANY_DB"], marker="o", linewidth=2, label="Articles Found")
    annotate_line_points(ax, df["YEAR"], df["FOUND_IN_ANY_DB"], formatter=lambda value: f"{int(value)}")
    plt.title(title)
    first_year = int(df["YEAR"].min())
    last_year = int(df["YEAR"].max())
    plt.xlabel(f"Year ({first_year}-{last_year})")
    plt.ylabel("Number of Articles")
    plt.grid(linestyle="--", alpha=0.25)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    return title


def plot_top_db_by_year(df: pd.DataFrame, out_path: Path, db_colors: dict[str, tuple[float, float, float, float]]) -> str:
    df = df.copy()
    df["YEAR"] = ensure_numeric(df, "YEAR")
    df["MATCHED_TITLES"] = ensure_numeric(df, "MATCHED_TITLES").fillna(0).astype(int)
    df = df.dropna(subset=["YEAR", "MATCHED_TITLES"])
    df["YEAR"] = df["YEAR"].astype(int)

    idx = df.groupby("YEAR")["MATCHED_TITLES"].idxmax()
    top = df.loc[idx].sort_values("YEAR")
    title = "Best Academic Database by Year"

    plt.figure(figsize=(11, 6))
    bars = plt.bar(top["YEAR"].astype(str), top["MATCHED_TITLES"], color=colors_for_dbs(top["DB"], db_colors))
    plt.title(title)
    plt.xlabel("Year")
    plt.ylabel("Number of Articles")
    plt.grid(axis="y", linestyle="--", alpha=0.25)
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))

    for bar, value in zip(bars, top["MATCHED_TITLES"]):
        x = bar.get_x() + bar.get_width() / 2
        plt.text(x, bar.get_height() / 2, f"{int(value)}", ha="center", va="center", fontsize=8, color="black")

    legend_dbs = list(dict.fromkeys(top["DB"].astype(str).tolist()))
    legend_handles = [
        Patch(facecolor=db_colors.get(db, (0.5, 0.5, 0.5, 1.0)), label=get_db_label(db))
        for db in legend_dbs
    ]
    plt.legend(handles=legend_handles, title="Academic Database", fontsize=8, loc="upper left", ncol=2)

    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    return title


def plot_direct_db_coverage(df: pd.DataFrame, out_path: Path, db_colors: dict[str, tuple[float, float, float, float]]) -> str:
    df = df.copy()
    col = "TARGET_ARTICLES_FOUND" if "TARGET_ARTICLES_FOUND" in df.columns else "TITLES_INDEXED"
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    df = df.sort_values(col, ascending=True)
    df["DB_LABEL"] = df["DB"].astype(str).apply(get_db_label)
    title = "Target Articles Found per Academic Database"

    plt.figure(figsize=(10, 7))
    bars = plt.barh(df["DB_LABEL"], df[col], color=colors_for_dbs(df["DB"], db_colors))
    plt.title(title)
    plt.xlabel("Number of Articles")
    plt.ylabel("Academic Database")
    plt.grid(axis="x", linestyle="--", alpha=0.3)
    plt.gca().xaxis.set_major_locator(MaxNLocator(integer=True))

    for bar, val in zip(bars, df[col]):
        plt.text(val + 0.2, bar.get_y() + bar.get_height() / 2, f"{int(val)}", va="center", fontsize=9)

    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    return title


def plot_direct_db_by_year(df: pd.DataFrame, out_path: Path, db_colors: dict[str, tuple[float, float, float, float]]) -> str:
    df = df.copy()
    df["YEAR"] = pd.to_numeric(df["YEAR"], errors="coerce")
    col = "TARGET_ARTICLES_FOUND" if "TARGET_ARTICLES_FOUND" in df.columns else "TITLES_INDEXED"
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    df = df.dropna(subset=["YEAR"])
    df["YEAR"] = df["YEAR"].astype(int)
    title = "Target Articles Found per Year by Academic Database"

    pivot = df.pivot_table(index="YEAR", columns="DB", values=col, aggfunc="sum", fill_value=0)
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
    ax.set_title(title)
    ax.set_xlabel("Year")
    ax.set_ylabel("Number of Articles")
    ax.grid(axis="y", linestyle="--", alpha=0.25)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    handles, labels = ax.get_legend_handles_labels()
    labels = [get_db_label(label) for label in labels]
    ax.legend(handles, labels, title="Academic Database", loc="upper left", fontsize=8, ncol=2)
    for container in ax.containers:
        labels = [f"{int(v)}" if v > 0 else "" for v in container.datavalues]
        ax.bar_label(container, labels=labels, label_type="center", fontsize=7, color="black")
    plt.xticks(rotation=0, ha="center", fontsize=9)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    return title


def plot_article_db_distribution(df: pd.DataFrame, out_path: Path) -> str:
    df = df.copy()
    df["DB_COUNT"] = pd.to_numeric(df["DB_COUNT"], errors="coerce").fillna(0).astype(int)
    df["ARTICLE_COUNT"] = pd.to_numeric(df["ARTICLE_COUNT"], errors="coerce").fillna(0).astype(int)
    df = df[df["DB_COUNT"] > 0].sort_values("DB_COUNT")
    title = "How Many Databases Find Each Target Article"

    plt.figure(figsize=(10, 6))
    bars = plt.bar(df["DB_COUNT"].astype(str), df["ARTICLE_COUNT"], color="#4c78a8")
    plt.title(title)
    plt.xlabel("Number of Databases that Found the Article")
    plt.ylabel("Number of Target Articles")
    plt.grid(axis="y", linestyle="--", alpha=0.25)
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))

    for bar, val in zip(bars, df["ARTICLE_COUNT"]):
        x = bar.get_x() + bar.get_width() / 2
        plt.text(x, val + 0.2, f"{int(val)}", ha="center", va="bottom", fontsize=9)

    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    return title


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate charts from DB completeness CSV outputs.")
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
        help="Directory containing analysis CSV files (default: src/dataout/SS{SS_ID}).",
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

    try:
        scope = resolve_search_scope(args.ss_id, args.config_csv)
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(f"[error] {exc}") from exc

    data_dir = Path(args.data_dir).resolve() if args.data_dir else get_scope_dataout_dir(scope.ss_id)
    out_dir = Path(args.out_dir).resolve() if args.out_dir else (data_dir / "charts")
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_dir = Path(args.csv_dir).resolve() if args.csv_dir else out_dir

    print(f"[info] SS_ID: {scope.ss_id}")
    print(f"[info] Scope dir: {data_dir}")

    direct_cov_path = csv_dir / "db_coverage_from_target.csv"
    direct_year_path = csv_dir / "db_from_target_by_year.csv"
    distribution_path = csv_dir / "article_db_match_distribution.csv"
    if not direct_cov_path.is_file() or not direct_year_path.is_file() or not distribution_path.is_file():
        missing = [
            str(path)
            for path in [direct_cov_path, direct_year_path, distribution_path]
            if not path.is_file()
        ]
        raise SystemExit("[error] missing chart input CSV files: " + ", ".join(missing))

    direct_cov = read_csv(direct_cov_path)
    direct_year = read_csv(direct_year_path)
    distribution = read_csv(distribution_path)

    all_dbs = set(direct_cov["DB"].astype(str)) | set(direct_year["DB"].astype(str))
    db_colors = build_db_color_map(list(all_dbs))

    direct_cov_title = "Target Articles Found per Academic Database"
    direct_cov_png = out_dir / slugify_title(direct_cov_title)
    plot_direct_db_coverage(direct_cov, direct_cov_png, db_colors)
    print(f"[out] {direct_cov_png}")

    direct_year_title = "Target Articles Found per Year by Academic Database"
    direct_year_png = out_dir / slugify_title(direct_year_title)
    plot_direct_db_by_year(direct_year, direct_year_png, db_colors)
    print(f"[out] {direct_year_png}")

    dist_title = "How Many Databases Find Each Target Article"
    dist_png = out_dir / slugify_title(dist_title)
    plot_article_db_distribution(distribution, dist_png)
    print(f"[out] {dist_png}")

    print(f"[ok] charts saved to: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())