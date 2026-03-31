#!/usr/bin/env python3

import argparse
import os
import sys
from pathlib import Path
import pandas as pd
import bibtexparser
import importlib

try:
    sys.stdout.reconfigure(line_buffering=True, write_through=True)
    sys.stderr.reconfigure(line_buffering=True, write_through=True)
except Exception:
    pass

# Interactive execution from the project root needs src added before package imports.
if "__file__" not in globals():
    sys.path.insert(0, str(Path.cwd() / "src"))

from db_search import functions as DBFunctions
from db_search import fun_words as FWords
from db_search.paths import ensure_src_on_path
from db_search.search_scope import (
    get_scope_dataout_dir,
    resolve_scoped_input_dir,
    resolve_search_scope,
)

ensure_src_on_path(__file__ if "__file__" in globals() else None)
importlib.reload(FWords)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract CSV/Bib records into the scoped output directory.")
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

DF = pd.DataFrame(columns=['DB', 'YEAR', 'TITLE'])  # , 'author'])

# 1) ======================================================
# Extract data from BibTeX files
BIB_DIR = resolve_scoped_input_dir(SCOPE.ss_id, "Bib")
if not BIB_DIR.is_dir():
    raise SystemExit(
        f"[error] Missing Bib input directory (scoped or legacy): {BIB_DIR}"
    )
# List all bib files in the dir
all_bib_files = sorted([f.name for f in BIB_DIR.iterdir() if f.suffix == '.bib'])

if not all_bib_files:
    raise SystemExit(
        f"[error] No .bib files found in scoped/legacy input directory: {BIB_DIR}"
    )

# Loop over every bib files in the folder
for file in all_bib_files:
    db_name = DBFunctions.get_db_name(file)  # Extract the database name from the filename
    print("BibTeX file: ", file, "... ", end='')
    file_path = BIB_DIR / file
    # Read the bibTex file and feed a Pandas DataFrame
    with open(file_path, encoding='utf-8') as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file)
    # Convert the bibTex entries to a Pandas DataFrame
    df = pd.DataFrame(bib_database.entries)
    df = df.head(200)  # Limit to first 200 records for testing
    df = df[['year', 'title']]  # , 'author']]
    df.columns = ["YEAR", "TITLE"]
    df.insert(0, 'DB', db_name)
    DF = pd.concat([DF, df], ignore_index=True)
    print("Records: ", len(df), "   Total:", len(DF), flush=True)


# 2) ======================================================
CSV_DIR = resolve_scoped_input_dir(SCOPE.ss_id, "CSV")
if not CSV_DIR.is_dir():
    raise SystemExit(
        f"[error] Missing CSV input directory (scoped or legacy): {CSV_DIR}"
    )
all_springer_files = sorted([f.name for f in CSV_DIR.iterdir() if f.name.startswith('SpringerNatureLink') and f.suffix == '.csv'])
# Loop over every Springer Nature CSV files in the folder
for file in all_springer_files:
    db_name = DBFunctions.get_db_name(file)  # Extract the database name from the filename
    print("CSV file: ", file, "... ", end='')
    file_path = CSV_DIR / file
    df = pd.read_csv(file_path, nrows=200)
    df = df[['Publication Year', 'Item Title']]
    df.columns = ["YEAR", "TITLE"]
    df.insert(0, 'DB', db_name)
    DF = pd.concat([DF, df], ignore_index=True)
    print("Records: ", len(df), "   Total:", len(DF))
    

# 3) ======================================================
all_taylor_files = sorted([f.name for f in CSV_DIR.iterdir() if f.name.startswith('Taylor') and f.suffix == '.csv'])
# Loop over every Taylor CSV files in the folder
for file in all_taylor_files:
    db_name = DBFunctions.get_db_name(file)  # Extract the database name from the filename
    print("CSV file: ", file, "... ", end='')
    file_path = CSV_DIR / file
    df = pd.read_csv(file_path, nrows=200, encoding="UTF-8")
    df = df[['Volume year', 'Article title']]
    df.columns = ["YEAR", "TITLE"]
    df.insert(0, 'DB', db_name)
    DF = pd.concat([DF, df], ignore_index=True)
    print("Records: ", len(df), "   Total:", len(DF))


# df = df.drop_duplicates(subset=['YEAR', 'TITLE'])  # , 'author'])
DF.TITLE = FWords.adj_title_array(DF.TITLE)
DF.value_counts('DB')
print(6)
# Write the combined DataFrame to a CSV file without the index and quotes around strings
output_path = SCOPE_OUT_DIR / 'CSV_and_Bib.csv'
DF.to_csv(output_path, index=False, sep=";", header=False)
print(f"[out] {output_path}")
# DF.to_csv('dataout/CSV_and_Bib.csv', index=False)
