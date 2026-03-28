import os
import re
import sys
import numpy as np
import importlib
import fitz  # PyMuPDF
from pathlib import Path

# Unindo todos os PDFs em apenas um
# pdfunite SemanticScholar/SS1P*.pdf Semantic_Scholar_Document_200_search_results1.pdf
# pdfunite SemanticScholar/SS2P*.pdf Semantic_Scholar_Document_200_search_results2.pdf

FILE_DIR = Path(__file__).resolve().parent
SRC_DIR = next((p for p in [FILE_DIR, *FILE_DIR.parents] if p.name == 'src'), FILE_DIR)
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from db_search import fun_colors as FCol
importlib.reload(FCol)

DIR_DATA_IN = '/home/jrmgarcia/ProjDocs/DB_Search/src/datain/PDF/SemanticScholar'
DIR_DATA_OUT = '/home/jrmgarcia/ProjDocs/DB_Search/src/dataout'

ss_num = 1  # PDFs from search string 1 (the default SS)
# ss_num = 2  # PDFs from search string 2 ("review wildfire spread prediction")

# Iterate among PDF files in the input directory
all_pdf_files = sorted([f for f in os.listdir(
    DIR_DATA_IN) if f.startswith(f'SS{ss_num}P') and f.endswith('.pdf')])

if ss_num == 1:
    size_title = 13.5
    size_meta = 10.5
    size_abstract = 12.0
else:
    size_title = 10.11584758758545
    size_meta = 7.8678812980651855
    size_abstract = 8.991864204406738


titles = []
years = []
cont_art = 0

# idx_file=0; file=all_pdf_files[idx_file]
for idx_file, file in enumerate(all_pdf_files):
    title = year = ""

    file_path = os.path.join(DIR_DATA_IN, file)
    DOC = fitz.open(file_path)

    # if idx_file > 0:
    #    break

    # Unite all blocks of the file
    text_blocks = []
    # idx_page=0; page=DOC.load_page(idx_page)
    for idx_page, page in enumerate(DOC):
        page_blocks = page.get_text("dict")["blocks"]
        for idx_block, block in enumerate(page_blocks):
            # idx_block = 0; block=text_blocks[idx_block]
            if block['type'] == 0:  # 0 indicates a text block
                text_blocks.append(block)
    print(file, ": ", len(text_blocks), " text blocks united!", sep="")

    # Titles are in blocks with size 13.5
    # Abstracts are in blocks with size 12.0
    # Years are the last text just before the abstract (if exists)

    # Iterate among blocks
    # idx_block = 0; block=text_blocks[idx_block]
    building = False
    for idx_block, block in enumerate(text_blocks):
        size = block["lines"][0]['spans'][0]['size']
        first_text = block['lines'][0]['spans'][0]['text'].strip()
        last_text = block['lines'][-1]['spans'][-1]['text'].strip()

        # Title
        # 34 last blocks can be ignored
        if size == size_title and idx_block < (len(text_blocks)-34):
            if not building:
                building = True
                title = ""
                year = "????"
                cont_art += 1
            for idx_line, line in enumerate(block['lines']):
                for idx_span, span in enumerate(line['spans']):
                    title += span['text'].replace('\n', ' ').strip() + ' '

        # Authors and Metadata
        elif size == size_meta and building:
            year_candidate = last_text
            year_match = re.search(r'\b(19|20)\d{2}\b', year_candidate)
            year = year_candidate if year_match else year

        # Abstract (end of paper analysis)
        elif size == size_abstract and building and first_text != "Expand":

            titles.append(" ".join(title.strip().split()).replace(
                " ,", ",").replace(" :", ":"))
            title = ""

            # year_match = re.search(r'\b(19|20)\d{2}\b', year_candidate)
            # year = year_candidate if year_match else "????"
            years.append(year)
            building = False
            print(cont_art, year, titles[-1])
        # else:
        #    building = False

assert len(titles) == len(years)

# Print the titles found
# for idx, t in enumerate(titles):
#     print(f"{idx+1:03d}: {years[idx]} {t}")


# Join the lists years and titles as a string separated by ";"
articles = [f"{db};{year};{title}" for db, year,
            title in zip(["Semantic" + str(ss_num)] * len(titles), years, titles)]
with open(f"{DIR_DATA_OUT}/SemanticScholar{ss_num}.csv", "w",
          encoding='utf-8') as file:
    for article in articles:
        x = file.write(f"{article}\n")
