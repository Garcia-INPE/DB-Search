import os
import fitz  # PyMuPDF

from db_search import fun_words as FWords
from db_search.paths import DATA_IN_DIR, DATA_OUT_DIR, ensure_src_on_path
ensure_src_on_path(__file__ if "__file__" in globals() else None)

# PDF 2 TXT
# command = "pdftotext datain/PDF/Scopus_Document_search_results.pdf"
# os.system(command)

# # Read the generated TXT file
# with open("datain/PDF/Scopus_Document_search_results.txt", "r",
#           encoding='utf-8') as file:
#     content = file.read()

DIR_DATA_IN = DATA_IN_DIR / 'PDF'
DIR_DATA_OUT = DATA_OUT_DIR
DOC = fitz.open(DIR_DATA_IN / 'Scopus_Document_200_search_results.pdf')

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
years = []
title = ""
# idx_page = 24; page = DOC.load_page(idx_page)

str_exclude = ["Country/territory", "Source type", "Source title", "Author name", "Document type", "Language Keyword", "Subject area", "Publication stage",
               "Affiliation", "Funding sponsor", "Open access", "Keyword", "Language", "Limited to", "Year", "Discover early research ideas"]

for idx_page, page in enumerate(DOC):
    text_blocks = page.get_text("dict")["blocks"]
    last_title_block = -10

    # idx_block = 31; block = text_blocks[idx_block]
    # idx_line = 0; line = block['lines'][idx_line]
    # idx_span = 0; span = line['spans'][idx_span]

    search_str = "year"   # title | year
    for idx_block, block in enumerate(text_blocks):
        if block['type'] == 0:  # 0 indicates a text block
            for idx_line, line in enumerate(block['lines']):
                if idx_line > 0 or idx_block != last_title_block:
                    title += ' '
                for idx_span, span in enumerate(line['spans']):
                    text = span['text']  # .strip()

                    # ------------------------------------------------
                    # Search for titles of the articles
                    # ------------------------------------------------
                    if span['flags'] == 20 and span['char_flags'] == 24 and span['font'] == 'ElsevierSansWeb-Bold' and not text in str_exclude:
                        # Start a new title if block index is neither current or previous
                        if idx_block in [last_title_block, last_title_block + 1]:
                            # title += ' ' + text + ' '
                            title += text
                        else:
                            # If there is some title stored, save it before starting a new one
                            if title.strip():
                                title = FWords.adj_title(title)
                                titles.append(title)
                                # print(titles[-1])

                            title = text

                        last_title_block = idx_block

                    # ------------------------------------------------
                    # Search for the years of the articles
                    # ------------------------------------------------
                    # Checkpoint
                    # if idx_page == 26 and idx_block == 16 and idx_line == 0 and idx_span == 0:
                    # x = span['xxx']
                    extracted_text.append(text.strip())

                    # Find the year of the article some indexes backwards "Show abstract" text
                    if extracted_text[-1] == "Show abstract":
                        # Goes backwards extracted_text list up to find the firt text like an year
                        for extracted_text_candidate in reversed(extracted_text[:-1]):
                            if extracted_text_candidate.isdigit() and len(extracted_text_candidate) == 4:
                                years.append(extracted_text_candidate)
                                extracted_text = []  # Clear the list for next search
                                break  # Stop after finding

                    # print(idx_page, idx_block, idx_line, idx_span, text)

# Store the last title found in the document
if title:
    titles.append(" ".join(title.split()).strip())

assert len(titles) == len(years)

# for idx, t in enumerate(titles):
# print(f"{idx+1:03d}: {t}")

# Join the lists years and titles as a string separated by ";"
articles = [f"{db};{year};{title}" for db, year,
            title in zip(["Scopus"] * len(titles), years, titles)]
with open(f"{DIR_DATA_OUT}/Scopus.csv", "w",
          encoding='utf-8') as file:
    for article in articles:
        x = file.write(f"{article}\n")
