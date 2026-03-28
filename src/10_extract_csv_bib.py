import os
import sys
from pathlib import Path
import pandas as pd
import bibtexparser
import importlib

# Interactive execution from the project root needs src added before package imports.
if "__file__" not in globals():
    sys.path.insert(0, str(Path.cwd() / "src"))

from db_search import fun_words as FWords
from db_search.paths import DATA_IN_DIR, DATA_OUT_DIR, ensure_src_on_path

ensure_src_on_path(__file__ if "__file__" in globals() else None)
importlib.reload(FWords)

DF = pd.DataFrame(columns=['DB', 'YEAR', 'TITLE'])  # , 'author'])

# 1) ======================================================
# Extract data from BibTeX files
BIB_DIR = DATA_IN_DIR / "Bib"
# List all bib files in the dir
all_bib_files = sorted([f.name for f in BIB_DIR.iterdir() if f.suffix == '.bib'])
file = all_bib_files[0]

# Loop over every bib files in the folder
for file in all_bib_files:
    db_name = FWords.get_db_name(file)  # Extract the database name from the filename
    print("BibTeX file: ", file, "... ", end='')
    file_path = BIB_DIR / file
    # Read the bibTex file and feed a Pandas DataFrame
    with open(file_path, encoding='utf-8') as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file)
    # Convert the bibTex entries to a Pandas DataFrame
    df = pd.DataFrame(bib_database.entries)
    df = df[['year', 'title']]  # , 'author']]
    df.columns = ["YEAR", "TITLE"]
    df.insert(0, 'DB', db_name)
    DF = pd.concat([DF, df], ignore_index=True)
    print("Records: ", len(df), "   Total:", len(DF))


# 2) ======================================================
CSV_DIR = DATA_IN_DIR / "CSV"
all_springer_files = sorted([f.name for f in CSV_DIR.iterdir() if f.name.startswith('SpringerNatureLink') and f.suffix == '.csv'])
file = all_springer_files[0]
# Loop over every Springer Nature CSV files in the folder
for file in all_springer_files:
    db_name = FWords.get_db_name(file)  # Extract the database name from the filename
    print("CSV file: ", file, "... ", end='')
    file_path = CSV_DIR / file
    df = pd.read_csv(file_path, nrows=200)
    df = df[['Publication Year', 'Item Title']]
    df.columns = ["YEAR", "TITLE"]
    df.insert(0, 'DB', db_name)
    DF = pd.concat([DF, df], ignore_index=True)
    print("Records: ", len(df), "   Total:", len(DF))
    

# 3) ======================================================
all_springer_files = sorted([f.name for f in CSV_DIR.iterdir() if f.name.startswith('Taylor') and f.suffix == '.csv'])
file = all_springer_files[0]
# Loop over every Springer Nature CSV files in the folder
for file in all_springer_files:
    db_name = FWords.get_db_name(file)  # Extract the database name from the filename
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
DF.to_csv(DATA_OUT_DIR / 'CSV_and_Bib.csv', index=False, sep=";", header=False)
# DF.to_csv('dataout/CSV_and_Bib.csv', index=False)
