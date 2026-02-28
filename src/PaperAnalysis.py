import os
# import enchant
import pandas as pd
import importlib
import FunWords as FWords
importlib.reload(FWords)

pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)

DIR_DATA_IN = '/home/jrmgarcia/ProjDocs/DB_Search/src/dataout/'
DIR_DATA_OUT = DIR_DATA_IN

# Load all CSV files into a Pandas dataframe
all_csv_files = sorted(
    [f for f in os.listdir(DIR_DATA_IN) if f.endswith('.csv')])

PAPERS = pd.DataFrame()
# idx_file=0; csv_file=all_csv_files[idx_file]
for idx_file, csv_file in enumerate(all_csv_files):
    file_path = os.path.join(DIR_DATA_IN, csv_file)
    df = pd.read_csv(file_path, sep=";", header=None, encoding="UTF-8")
    print(csv_file, len(df))
    PAPERS = pd.concat([PAPERS, df], ignore_index=True)
#
PAPERS.columns = ['DB', 'YEAR', 'TITLE']

print("Original size:", len(PAPERS))

PAPERS.TITLE = FWords.adj_title_array(PAPERS.TITLE)
PAPERS.TITLE = PAPERS.TITLE.str.lower()
PAPERS.sort_values("TITLE", inplace=True)
PAPERS.drop_duplicates('TITLE', inplace=True)
PAPERS.reset_index(inplace=True)
# PAPERS[810:813]
# for i in range(len(PAPERS.iloc[43]["TITLE"])):
#     char1 = PAPERS.iloc[43]["TITLE"][i]
#     char2 = PAPERS.iloc[44]["TITLE"][i]
#     print(char1, ord(char1), char2, ord(char2), char1 == char2)

# PAPERS[PAPERS["DB"] == "SemSch2"]['TITLE']

t = pd.Series(PAPERS["TITLE"])
t2 = ';' + t.astype(str)
t2.to_csv("TITLES.txt", index=False,
          header=False)


# Further steps to prepare to list of ok articles
# 1) Replace "\ by ;"
# 2) Remove all "
# 3) Changes in title treatment for equalizing diff symbols:
#    . words written together, "acents", lower case, false identical symbols,
# 4) Analise and annotate 1763 titles 0=NOT OK, 1=OK for being a review in WFP or WFSP (and keyword variations)
#    . initial filter


# Create a dictionary object for American English
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
