import os
import sys
from pathlib import Path
import pandas as pd
import importlib
from pandas.errors import EmptyDataError

# Interactive execution from the project root needs src added before package imports.
if "__file__" not in globals() and str(Path.cwd() / "src") not in sys.path:
    sys.path.insert(0, str(Path.cwd() / "src"))

from db_search import fun_words as FWords
from db_search.paths import DATA_OUT_DIR, ensure_src_on_path

ensure_src_on_path(__file__ if "__file__" in globals() else None)
importlib.reload(FWords)

pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)

DIR_DATA_IN = DATA_OUT_DIR
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
(DATA_OUT_DIR / "01-TITLES_RAW.csv").write_text("\n".join(t2) + "\n", encoding="utf-8")

# Keep only titles with the requested search logic:
# (review OR survey) AND (wildfire OR 'wild fire' OR 'forest fire')
str_set1 = r"(?:review|survey)"
str_set2 = r"(?:wildfire|wild fire|forest fire)"
good = PAPERS["TITLE"].str.contains(str_set1, na=False) & PAPERS["TITLE"].str.contains(str_set2, na=False)
PAPERS_REVIEW_WF = PAPERS[good].copy()
PAPERS_REVIEW_WF.reset_index(inplace=True, drop=True)
# Persist as CSV
PAPERS_REVIEW_WF.to_csv(DATA_OUT_DIR / "02-TITLES_REVIEW_WF.csv", index=False, encoding="utf-8", sep=";")

# Further steps to prepare to list of ok articles
# 1) Replace "\ by ;"
# 2) Remove all "
# 3) Changes in title treatment for equalizing diff symbols:
#    . words written together, "acents", lower case, false identical symbols,
# 4) Analise and annotate 1763 titles 0=NOT OK, 1=OK for being a review in WFP or WFSP (and keyword variations)
#    . initial filter


# Create a dictionary object for American English
import enchant
d = enchant.Dict("en_US")
out_words = []
in_words = []
# Iterate through each entry in the column TITLE
for sentence in PAPERS['TITLE']:
    # Split each sentence into a list of words
    for word in sentence.split():
        word_ok = FWords.clean_word(word)
        if word_ok:
            for w in word_ok.split():
                if not d.check(w):
                    out_words.append(w)

out_words = sorted(set(out_words))
len(out_words)
