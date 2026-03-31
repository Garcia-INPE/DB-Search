#!/usr/bin/env python3

import argparse
import os
import sys
from html import escape
from pathlib import Path
import pandas as pd
import importlib
from pandas.errors import EmptyDataError

try:
    sys.stdout.reconfigure(line_buffering=True, write_through=True)
    sys.stderr.reconfigure(line_buffering=True, write_through=True)
except Exception:
    pass

# Interactive execution from the project root needs src added before package imports.
if "__file__" not in globals() and str(Path.cwd() / "src") not in sys.path:
    sys.path.insert(0, str(Path.cwd() / "src"))

from db_search import fun_words as FWords
from db_search.functions import get_db_label
from db_search.paths import DATA_OUT_DIR, ensure_src_on_path
from db_search.search_scope import get_scope_dataout_dir, resolve_search_scope

ensure_src_on_path(__file__ if "__file__" in globals() else None)
importlib.reload(FWords)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze extracted papers in a scoped output directory.")
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
    return parser.parse_args()


ARGS = parse_args()
try:
    SCOPE = resolve_search_scope(ARGS.ss_id, ARGS.config_csv)
except (FileNotFoundError, ValueError) as exc:
    raise SystemExit(f"[error] {exc}") from exc

SCOPE_OUT_DIR = get_scope_dataout_dir(SCOPE.ss_id)
SCOPE_OUT_DIR.mkdir(parents=True, exist_ok=True)
print(f"[info] SS_ID: {SCOPE.ss_id}")
print(f"[info] Scope dir: {SCOPE_OUT_DIR}")

pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)

DIR_DATA_IN = SCOPE_OUT_DIR
DIR_DATA_OUT = DIR_DATA_IN

# Load only source extraction CSV files (exclude derived analysis outputs).
source_csv_files = [
    "CSV_and_Bib.csv",
    "GoogleScholar.csv",
    "SemanticScholar.csv",
]
all_csv_files = [f for f in source_csv_files if (DIR_DATA_IN / f).is_file()]

if not all_csv_files:
    raise FileNotFoundError("No source CSV files found in dataout: CSV_and_Bib.csv, GoogleScholar.csv, SemanticScholar.csv")

PAPERS = pd.DataFrame()
loaded_csv_files = []
skipped_csv_files = []
# idx_file=0; csv_file=all_csv_files[idx_file]
for idx_file, csv_file in enumerate(all_csv_files):
    file_path = os.path.join(DIR_DATA_IN, csv_file)
    try:
        df = pd.read_csv(file_path, sep=";", header=None, encoding="UTF-8")
    except EmptyDataError:
        print(f"[warn] skipped empty CSV: {csv_file}")
        skipped_csv_files.append(csv_file)
        continue

    if df.empty:
        print(f"[warn] skipped empty CSV: {csv_file}")
        skipped_csv_files.append(csv_file)
        continue

    print(csv_file, len(df))
    PAPERS = pd.concat([PAPERS, df], ignore_index=True)
    loaded_csv_files.append(csv_file)
#
if PAPERS.empty:
    raise FileNotFoundError(
        "No readable source CSV data found in dataout: " + ", ".join(all_csv_files)
    )

PAPERS.columns = ['DB', 'YEAR', 'TITLE']

if skipped_csv_files:
    print("[warn] skipped source CSV files:", ", ".join(skipped_csv_files))

print("Original size:", len(PAPERS))

# Remove empty lines
PAPERS.dropna(subset=['TITLE'], inplace=True)
PAPERS.TITLE = FWords.adj_title_array(PAPERS.TITLE, del_quotes=True)
PAPERS.TITLE = PAPERS.TITLE.str.lower()
PAPERS_ALL = PAPERS.copy()
PAPERS.sort_values("TITLE", inplace=True)
PAPERS.drop_duplicates('TITLE', inplace=True)
PAPERS.reset_index(inplace=True, drop=True)
#PAPERS.columns
# PAPERS[810:813]
# for i in range(len(PAPERS.iloc[43]["TITLE"])):
#     char1 = PAPERS.iloc[43]["TITLE"][i]
#     char2 = PAPERS.iloc[44]["TITLE"][i]
#     print(char1, ord(char1), char2, ord(char2), char1 == char2)

t = pd.Series(PAPERS["TITLE"])
t2 = ';' + t.astype(str)
(DIR_DATA_OUT / "01-TITLES_RAW.csv").write_text("\n".join(t2) + "\n", encoding="utf-8")

# Keep only titles with the requested search logic:
# (review OR survey) AND (wildfire OR 'wild fire' OR 'forest fire')
str_set1 = r"(?:review|survey)"
str_set2 = r"(?:wildfire|wild fire|forest fire)"
good = PAPERS["TITLE"].str.contains(str_set1, na=False) & PAPERS["TITLE"].str.contains(str_set2, na=False)
PAPERS_REVIEW_WF = PAPERS[good].copy()
PAPERS_REVIEW_WF.reset_index(inplace=True, drop=True)
# Persist as CSV
PAPERS_REVIEW_WF[["YEAR", "TITLE"]].to_csv(DIR_DATA_OUT / "02-TITLES_REVIEW_WF.csv", index=False, encoding="utf-8", sep=";")

# Build a presence matrix where each target paper row has one column per DB.
db_columns = sorted(PAPERS_ALL["DB"].dropna().astype(str).str.strip().unique().tolist())
title_db_pairs = PAPERS_ALL[["TITLE", "DB"]].dropna().copy()
title_db_pairs["TITLE"] = title_db_pairs["TITLE"].astype(str).str.strip()
title_db_pairs["DB"] = title_db_pairs["DB"].astype(str).str.strip()
title_db_pairs = title_db_pairs[(title_db_pairs["TITLE"] != "") & (title_db_pairs["DB"] != "")]
title_db_pairs = title_db_pairs.drop_duplicates()
title_db_pairs["FOUND"] = 1

title_db_pivot = title_db_pairs.pivot_table(
    index="TITLE",
    columns="DB",
    values="FOUND",
    aggfunc="max",
    fill_value=0,
)

matrix_df = PAPERS_REVIEW_WF[["YEAR", "TITLE"]].copy()
matrix_df.insert(0, "IDX", matrix_df.index)
matrix_df = matrix_df.join(title_db_pivot, on="TITLE")

for db_col in db_columns:
    if db_col not in matrix_df.columns:
        matrix_df[db_col] = 0
matrix_df[db_columns] = matrix_df[db_columns].fillna(0).astype(int)
matrix_df = matrix_df[["IDX", "YEAR", *db_columns]].copy()

matrix_csv_path = DIR_DATA_OUT / "02-TITLES_REVIEW_WF_DB_MATRIX.csv"
matrix_df.to_csv(matrix_csv_path, index=False, encoding="utf-8", sep=";")

pretty_columns = {db: db for db in db_columns}
pretty_db_columns = [pretty_columns[db] for db in db_columns]
html_df = matrix_df.rename(columns=pretty_columns).copy()

summary_html = (
    "<div style='margin: 0 0 14px 0; padding: 12px; border-radius: 10px; "
    "background: linear-gradient(120deg, #eef6ff, #f7fbff); border: 1px solid #cfe2ff;'>"
    "<h2 style='margin: 0 0 6px 0; font-family: Arial, sans-serif;'>Review/Survey x DB Presence Matrix</h2>"
    f"<p style='margin: 0; font-family: Arial, sans-serif; color: #334155;'>Rows: {len(matrix_df)} target papers | "
    f"DB columns: {len(db_columns)} | Source files used: {len(loaded_csv_files)}</p>"
    "</div>"
)

matrix_html_path = DIR_DATA_OUT / "02-TITLES_REVIEW_WF_DB_MATRIX.html"

header_cells_list = []
for col in html_df.columns:
    if col in pretty_db_columns:
        full_label = get_db_label(col)
        header_cells_list.append(f"<th class='db' title='{escape(full_label)}'>{escape(str(col))}</th>")
    elif col == "IDX":
        header_cells_list.append("<th class='idx'>IDX</th>")
    elif col == "YEAR":
        header_cells_list.append("<th class='year'>YEAR</th>")
    else:
        header_cells_list.append(f"<th>{escape(str(col))}</th>")
header_cells = "".join(header_cells_list)
body_rows = []
for _, row in html_df.iterrows():
    cells = []
    for col in html_df.columns:
        val = row[col]
        if col in pretty_db_columns:
            found = int(val) == 1
            cls = "found" if found else "miss"
            text = "1" if found else "0"
            cells.append(f"<td class='{cls}'>{text}</td>")
        elif col == "IDX":
            cells.append(f"<td class='idx'>{escape(str(val))}</td>")
        elif col == "YEAR":
            cells.append(f"<td class='year'>{escape(str(val))}</td>")
        else:
            cells.append(f"<td>{escape(str(val))}</td>")
    body_rows.append("<tr>" + "".join(cells) + "</tr>")

table_html = (
    "<table><thead><tr>"
    + header_cells
    + "</tr></thead><tbody>"
    + "".join(body_rows)
    + "</tbody></table>"
)

css = """
<style>
body { margin: 20px; background: #ffffff; font-family: Arial, sans-serif; }
table { border-collapse: collapse; width: 100%; }
th { position: sticky; top: 0; background: #1f2937; color: #ffffff; padding: 8px; border: 1px solid #e5e7eb; white-space: nowrap; }
td { padding: 6px 8px; border: 1px solid #e5e7eb; }
tbody tr:nth-child(even) { background-color: #f9fafb; }
th.idx, td.idx { width: 56px; min-width: 56px; text-align: center; }
th.year, td.year { width: 72px; min-width: 72px; text-align: center; }
th.db { width: 62px; min-width: 62px; text-align: center; font-size: 11px; }
td.found { background-color: #d9f2d9; color: #0f5132; text-align: center; font-weight: 700; }
td.miss { background-color: #f8f9fa; color: #adb5bd; text-align: center; }
</style>
"""

matrix_html_path.write_text(
    "<html><head><meta charset='utf-8'><title>02-TITLES_REVIEW_WF DB Matrix</title>"
    + css
    + "</head>"
    + f"<body>{summary_html}{table_html}</body></html>",
    encoding="utf-8",
)

print(f"[out] {matrix_csv_path}")
print(f"[out] {matrix_html_path}")

# Further steps to prepare to list of ok articles
# 1) Replace "\ by ;"
# 2) Remove all "
# 3) Changes in title treatment for equalizing diff symbols:
#    . words written together, "acents", lower case, false identical symbols,
# 4) Analise and annotate 1763 titles 0=NOT OK, 1=OK for being a review in WFP or WFSP (and keyword variations)
#    . initial filter


# Create a dictionary object for American English
# import enchant
# d = enchant.Dict("en_US")
# out_words = []
# in_words = []
# # Iterate through each entry in the column TITLE
# for sentence in PAPERS['TITLE']:
#     # Split each sentence into a list of words
#     for word in sentence.split():
#         word_ok = FWords.clean_word(word)
#         if word_ok:
#             for w in word_ok.split():
#                 if not d.check(w):
#                     out_words.append(w)

# out_words = sorted(set(out_words))
# len(out_words)
