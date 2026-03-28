import os
import re
import sys
import importlib
import fitz  # PyMuPDF
from pathlib import Path


# PDF 2 TXT
# command = "pdfunite Pages/*.pdf ../GoogleScholar_Document_200_search_results.pdf"
# os.system(command)

# # Read the generated TXT file
# with open("datain/PDF/Scopus_Document_search_results.txt", "r",
#           encoding='utf-8') as file:
#     content = file.read()

FILE_DIR = Path(__file__).resolve().parent
SRC_DIR = next((p for p in [FILE_DIR, *FILE_DIR.parents] if p.name == 'src'), FILE_DIR)
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from db_search import fun_colors as FCol
importlib.reload(FCol)


DIR_DATA_IN = '/home/jrmgarcia/ProjDocs/DB_Search/src/datain/PDF'
DIR_DATA_OUT = '/home/jrmgarcia/ProjDocs/DB_Search/src/dataout'
DOC = fitz.open(f"{DIR_DATA_IN}/GoogleScholar_Document_200_search_results.pdf")

extracted_text = []
span_color_set_dec = set()


# page_num = 1
# page = DOC.load_page(page_num)  # Load the pages by index (0-based)
# # blocks: 26, 34
# text_blocks = page.get_text("dict")["blocks"]
# idx_block=16; block=text_blocks[idx_block]
# idx_line=0; line=block['lines'][idx_line]
# idx_span=0; span=line['spans'][idx_span]
# print(span, len(text_blocks), len(block['lines']), len(line['spans']))
# for idx_block, block in enumerate(text_blocks):
#     if block['type'] == 0:  # 0 indicates a text block
#         for idx_line, line in enumerate(block['lines']):
#             for idx_span, span in enumerate(line['spans']):
#                 if span['flags'] == 20 and span['char_flags'] == 24 and span['font'] == 'ElsevierSansWeb-Bold' and len(block['lines']) > 1:
#                     print(idx_block, idx_line, idx_span, span['text'])


titles = []
metas = []
years = []
title = ""
meta = ""
# idx_page = 24; page = DOC.load_page(idx_page)

for idx_page, page in enumerate(DOC):
    text_blocks = page.get_text("dict")["blocks"]
    last_meta_block = -10

    # idx_block = 0; block = text_blocks[idx_block]
    # idx_line = 0; line = block['lines'][idx_line]
    # idx_span = 0; span = line['spans'][idx_span]

    search_str = "year"   # title | year
    for idx_block, block in enumerate(text_blocks):
        if block['type'] == 0:  # 0 indicates a text block
            for idx_line, line in enumerate(block['lines']):
                for idx_span, span in enumerate(line['spans']):
                    text = span['text'].replace('\n', ' ').strip()

                    # Checkpoint
                    # if idx_page == 0 and idx_block == 16 and idx_line == 0 and idx_span == 0:
                    #     for l in block['lines']:
                    #         for s in l['spans']:
                    #             print(s, "\n")
                    #     x = span['xxx']

                    # ------------------------------------------------
                    # Search for titles of the articles
                    # ------------------------------------------------
                    if span['size'] == 12.0 and span['flags'] in [0, 16] and span['char_flags'] in [16, 24] and span['font'] in ['ArialMT', 'Arial-BoldMT'] and span['color'] in [255, 6684825, 1707435]:
                        # print(idx_page, idx_block, idx_line, idx_span, text)
                        extracted_text.append(
                            f"{idx_page} {idx_block} {idx_line} {idx_span} {text}")
                        # print(extracted_text[-1])

                        # Start a new title if indexes of line and span are 0
                        if idx_line == 0 and idx_span == 0:
                            # If there is some title stored, save it before starting a new one
                            if title:
                                titles.append(" ".join(title.split()).replace(
                                    " ,", ",").replace(" :", ":"))
                                title = ""

                        title += " " + text

                    # ------------------------------------------------
                    # Search for the metadata and of the articles (contain the years)
                    # ------------------------------------------------
                    if span['size'] == 9.0 and span['flags'] in [0, 16] and span['char_flags'] in [16, 24] and span['font'] in ['ArialMT', 'Arial-BoldMT'] and span['color'] == 32768:
                        # and idx_block % 2 == 0 and idx_line == 0:

                        # print(idx_page, idx_block, idx_line, idx_span, text)

                        # If there is some metadata stored, save it before starting a new one
                        if idx_block == last_meta_block:
                            meta += " " + text
                        else:
                            # If there is some metadata stored, save it before starting a new one
                            if meta:
                                metas.append(
                                    " ".join(meta.split()).strip())
                            meta = text

                        last_meta_block = idx_block

# PRINT EXTRACTED TEXT
# for line in extracted_text:
#     print(line)


if title:
    titles.append(" ".join(title.split()).replace(
        " ,", ",").replace(" :", ":"))

if metas:
    metas.append(" ".join(meta.split()).strip())

# Find a year in every elemento of metas using regular expression
for idx, text in enumerate(metas):
    year_match = re.search(r'[,-] \b(19|20)\d{2}\b', text)
    if year_match:
        years.append(year_match.group(0).strip(' ,-'))
    else:
        print(
            f"Year not found in meta {idx}: '{text}'")


# Print the titles found
# for idx, t in enumerate(titles):
    # print(f"{idx+1:03d}: {t}")

assert len(titles) == len(metas) == len(years)

# Join the lists years and titles as a string separated by ";"
articles = [f"{db};{year};{title}" for db, year,
            title in zip(["Scholar"] * len(titles), years, titles)]
with open(f"{DIR_DATA_OUT}/GoogleScholar.csv", "w",
          encoding='utf-8') as file:
    for article in articles:
        x = file.write(f"{article}\n")
