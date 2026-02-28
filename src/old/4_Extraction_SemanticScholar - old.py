import os
import re
import sys
import numpy as np
import importlib
import fitz  # PyMuPDF

# pdfunite SemanticScholar/SS1P*.pdf Semantic_Scholar_Document_200_search_results1.pdf
# pdfunite SemanticScholar/SS2P*.pdf Semantic_Scholar_Document_200_search_results2.pdf

# Add the parent directory to sys.path to import custom modules
current_dir = os.path.dirname(__name__)
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
if not parent_dir in sys.path:
    sys.path.append(parent_dir)

# Import the package FunColors from the parent directory
import FunColors as FCol  # Custom module for color conversions # nopep8
importlib.reload(FCol)

DIR_DATA_IN = '/home/jrmgarcia/ProjDocs/DB_Search/src/datain/PDF'
DIR_DATA_OUT = '/home/jrmgarcia/ProjDocs/DB_Search/src/dataout'

# Iterate among PDF files in the input directory
pdf_file = "Semantic_Scholar_Document_200_search_results999.pdf"
# pdf_file = "SS999P01.pdf"

ss_num = 1
for ss_num in [1]:

    titles = []
    metas = []
    years = []
    title = meta = ""
    extracted_text = []

    # for idx_file, file in enumerate(all_pdf_files):
    file_path = os.path.join(DIR_DATA_IN, pdf_file.replace("999", str(ss_num)))
    # idx_file=0; file = all_pdf_files[idx_file]
    DOC = fitz.open(file_path)

    if idx_file > 0:
        break

    # idx_page = 0; page = DOC.load_page(idx_page)
    for idx_page, page in enumerate(DOC):

        if idx_page == 5:
            break

        text_blocks = page.get_text("dict")["blocks"]
        last_meta_block = -10

        # idx_block = 11; block=text_blocks[idx_block]
        for idx_block, block in enumerate(text_blocks):

            if block['type'] != 0:  # 1 indicates a binary block??
               x = 0
            else:
               size = block['lines'][0]['spans'][0]['size']
               first_text = block['lines'][0]['spans'][0]['text']
               last_text = block['lines'][-1]['spans'][-1]['text']
               print(str(ss_num), str(idx_page), str(idx_block), str(idx_line), str(idx_span),
                     " s:", size, " ft:", first_text, " lt:", last_text)

                # print(ss_num, idx_page, idx_block)
                # idx_line=0; line=block['lines'][idx_line]
                # import pprint
                # pprint.pprint(block['lines'])

                for idx_line, line in enumerate(block['lines']):
                    for idx_span, span in enumerate(line['spans']):
                        text = span['text'].replace('\n', ' ').strip()
                        if text.strip():
                            extracted_text.append(" ".join([str(ss_num), str(idx_page), str(idx_block),
                                                            str(idx_line), str(idx_span), text, "c:", str(span['color']), "s:", str(span['size']), "a:", str(span['ascender']), "d:", str(span['descender'])]))

                        # Checkpoint
                        # if ss_num == 1 and idx_page == 78 and idx_block == 18 and idx_line == 0 and idx_span == 4:
                        # if "H.Lee" in text:
                        #     #     #     year_match = re.search(
                        #     #     #         r'\b(19|20)\d{2}\b', text)
                        #     #     #     if year_match:
                        #     #     #     print(ss_num, idx_page, idx_block,
                        #     #     #           idx_line, idx_span, text, "s:", span['size'], "a:", span['ascender'], "d:", span['descender'])
                        #     for l in block['lines']:
                        #         for s in l['spans']:
                        #             print(s, "\n")
                        #     x = span['xxx']

                        # ------------------------------------------------
                        # Search for titles of the articles
                        # ------------------------------------------------
                        if (ss_num == 1 and span['size'] == 13.5 and span['flags'] == 0 and span['char_flags'] == 0 and span['font'] == 'Unnamed-T3' and span['color'] == 0) or \
                                (ss_num == 2 and span['size'] == 10.11584758758545 and span['flags'] == 0 and span['char_flags'] == 0 and span['font'] == 'Unnamed-T3' and span['color'] == 0) and \
                                block['lines'][-1]['spans'][-1]['text'] != "Cite":
                            # print(ss_num, idx_block, idx_line, idx_span, text)
                            #    extracted_text.append(
                            #        f"{idx_page} {idx_block} {idx_line} {idx_span} {text}")
                            #     print(extracted_text[-1])

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
                        year_match = re.search(r'\b(19|20)\d{2}\b', text)
                        if year_match:
                            # print(ss_num, idx_page, idx_block,
                            #      idx_line, idx_span, text, "s:", span['size'], "a:", span['ascender'], "d:", span['descender'], end='')

                            if ((ss_num == 1 and block['lines'][-1]['spans'][-1]['size'] == 10.5) or
                                    (ss_num == 2 and block['lines'][-1]['spans']
                                     [-1]['size'] == 7.8678812980651855)) and \
                                    block['lines'][-1]['spans'][-1]['font'] == 'Unnamed-T3' and \
                                    idx_span == len(block['lines'][-1]['spans'])-1:
                                # year_match:
                                year = year_match.group(0)
                                years.append(year)
                                print()
                            else:
                                print("****")

                        # If there is some metadata stored, save it before starting a new one
                        # if idx_block == last_meta_block:
                        #     meta += " " + text
                        # else:
                        #     # If there is some metadata stored, save it before starting a new one
                        #     if meta:
                        #         metas.append(
                        #             " ".join(meta.split()).strip())
                        #     meta = text

                        # last_meta_block = idx_block

# save e xtracted_text to ASCII file
np.savetxt('output.txt', extracted_text, fmt='%s')

   if title:
        titles.append(" ".join(title.split()).replace(
            " ,", ",").replace(" :", ":"))

    title_to_exclude = ["What Is Semantic Scholar?", "Help", "About", "Product", "API", "Research",
                        "What Is Semantic Scholar? About Product API Research Help"]
    # Remove elements from titles that matches the elements in the array
    titles = [x for x in titles if not x in title_to_exclude]

    # Join every line of titles with the previous line that starts with lowercase char
    for i in range(len(titles)-1, 0, -1):
        # check if the first char is lowercase
        if titles[i][0] == titles[i][0].lower() and titles[i][0].isdigit():
            titles[i-1] = titles[i-1] + " " + titles[i]
            x = titles.pop(i)

    # Print the titles found
    # for idx, t in enumerate(titles):
    #     print(f"{idx+1:03d}: {t}")

    # Print the years found
    # for idx, y in enumerate(years):
    #     print(f"{idx+1:03d}: {y}")

    assert len(titles) == len(years)

    # Join the lists years and titles as a string separated by ";"
    articles = [f"{db};{year};{title}" for db, year,
                title in zip(["Semantic" + str(ss_num)] * len(titles), years, titles)]
    with open(f"{DIR_DATA_OUT}/SemanticScholar{ss_num}.csv", "w",
              encoding='utf-8') as file:
        for article in articles:
            x = file.write(f"{article}\n")
