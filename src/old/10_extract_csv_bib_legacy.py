import os
import pandas as pd
import bibtexparser
import importlib

from db_search import fun_words as FWords
from db_search.paths import DATA_IN_DIR, DATA_OUT_DIR, ensure_src_on_path
ensure_src_on_path(__file__ if "__file__" in globals() else None)
importlib.reload(FWords)

DF = pd.DataFrame(columns=['DB', 'YEAR', 'TITLE'])  # , 'author'])

# 1) ======================================================
db_name = 'WebSci'  # Web of Science
# =========================================================
print(db_name, "... ", end='')
file_path = DATA_IN_DIR / "Bib" / "WebOfScience_Document_search_results.bib"
# Read the bibTex file and feed a Pandas DataFrame
with open(file_path, encoding='utf-8') as bibtex_file:
    bib_database = bibtexparser.load(bibtex_file)
# Convert the bibTex entries to a Pandas DataFrame
df = pd.DataFrame(bib_database.entries)
df = df[['year', 'title']]  # , 'author']]
df.columns = ["YEAR", "TITLE"]
df.insert(0, 'DB', db_name)
DF = pd.concat([DF, df], ignore_index=True)
print("Ok!")

# 2) ======================================================
db_name = 'ACM_DL'  # ACM Digital Library
# =========================================================
print(db_name, "... ", end='')
file_path = DATA_IN_DIR / "Bib" / "acm.bib"
# Read the bibTex file and feed a Pandas DataFrame
with open(file_path, encoding='utf-8') as bibtex_file:
    bib_database = bibtexparser.load(bibtex_file)
# Convert the bibTex entries to a Pandas DataFrame
df = pd.DataFrame(bib_database.entries)
df = df[['year', 'title']]  # , 'author']]
# Keep only the first 200 rows
df = df.head(200)
df.columns = ["YEAR", "TITLE"]
df.insert(0, 'DB', db_name)
DF = pd.concat([DF, df], ignore_index=True)
print("Ok!")

# 3) ======================================================
db_name = 'IEEEXp'
# =========================================================
print(db_name, "... ", end='')
file_path = DATA_IN_DIR / "CSV" / "IEEEXplore_export2025.10.14-14.23.20.csv"
df = pd.read_csv(file_path, nrows=200)
df = df[['Publication Year', 'Document Title']]  # , 'Authors']]
df.columns = ["YEAR", "TITLE"]
df.insert(0, 'DB', db_name)
DF = pd.concat([DF, df], ignore_index=True)
print("Ok!")

# 4) ======================================================
db_name = 'Sprger'  # Springer Nature
# =========================================================
print(db_name, "... ", end='')
file_path = DATA_IN_DIR / "CSV" / "SpringerNatureLink-SearchResults-2025.09.24.csv"
df = pd.read_csv(file_path, nrows=200)
df = df[['Publication Year', 'Item Title']]  # , 'Authors']]
df.columns = ["YEAR", "TITLE"]
df.insert(0, 'DB', db_name)
DF = pd.concat([DF, df], ignore_index=True)
print("Ok!")

# 5) ======================================================
db_name = 'TayFra'   # Taylor & Francis
# =========================================================
print(db_name, "... ", end='')
file_path = DATA_IN_DIR / "CSV" / "Taylor and Francis search results (28 October 2025).csv"
df = pd.read_csv(file_path, nrows=200, encoding="UTF-8")
df = df[['Volume year', 'Article title']]  # , 'Authors']]
df.columns = ["YEAR", "TITLE"]
df.insert(0, 'DB', db_name)
DF = pd.concat([DF, df], ignore_index=True)
print("Ok!")

# 6) ======================================================
db_name = 'Wiley'
# =========================================================
print(db_name, "... ", end='')
path = DATA_IN_DIR / "Bib" / "Wiley"
# Loop over every bib files in the folder
all_bib_files = sorted([f for f in os.listdir(path) if f.endswith('.bib')])
file = all_bib_files[0]
for file in all_bib_files:
    file_path = os.path.join(path, file)
    # Read the bibTex file and feed a Pandas DataFrame
    with open(file_path, encoding='utf-8') as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file)
    # Convert the bibTex entries to a Pandas DataFrame
    df = pd.DataFrame(bib_database.entries)
    df = df[['year', 'title']]  # , 'author']]
    df.columns = ["YEAR", "TITLE"]
    df.insert(0, 'DB', db_name)
    DF = pd.concat([DF, df], ignore_index=True)
print("Ok!")


# df = df.drop_duplicates(subset=['YEAR', 'TITLE'])  # , 'author'])
DF.TITLE = FWords.adj_title_array(DF.TITLE)
DF.value_counts('DB')
print(6)
# Write the combined DataFrame to a CSV file without the index and quotes around strings
DF.to_csv(DATA_OUT_DIR / 'CSV_and_Bib.csv', index=False, sep=";", header=False)
# DF.to_csv('dataout/CSV_and_Bib.csv', index=False)
