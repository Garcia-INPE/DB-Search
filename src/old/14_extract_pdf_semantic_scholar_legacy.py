import os
import sys
import re
import fitz  # PyMuPDF
from pathlib import Path

try:
    SRC_DIR = Path(__file__).resolve().parent
except NameError:
    cwd = Path.cwd().resolve()
    SRC_DIR = cwd / 'src' if (cwd / 'src').is_dir() else cwd

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from db_search import fun_words as FWords
from db_search.paths import DATA_IN_DIR, DATA_OUT_DIR

# Unindo todos os PDFs em apenas um
# pdfunite SemanticScholar/SS1P*.pdf Semantic_Scholar_Document_200_search_results1.pdf
# pdfunite SemanticScholar/SS2P*.pdf Semantic_Scholar_Document_200_search_results2.pdf

DIR_DATA_IN = DATA_IN_DIR / 'PDF' / 'SemanticScholar'
DIR_DATA_OUT = DATA_OUT_DIR

results = []
# Loop among 2 search strings
# ss_num = 1  # PDFs from search string 1 (the default SS)
# ss_num = 2  # PDFs from search string 2 ("review wildfire spread prediction")
ss_num = 1
for ss_num in [1, 2]:
    # Get the names of all PDF files in the input directory
    all_pdf_files = sorted([f for f in os.listdir(
        DIR_DATA_IN) if f.startswith(f'SS{ss_num}') and f.endswith('.pdf')])

    cont_art = 0
    titles = []
    years = []

    if ss_num == 1:
        size_title = 13.5
        size_meta = 10.5
        size_abstract = 12.0
    else:
        size_title = 10.11584758758545
        size_meta = 7.8678812980651855
        size_abstract = 8.991864204406738

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
        # print(file, ": ", len(text_blocks), " text blocks united!", sep="")

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

            # To get the title - it is a mark between titles
            # 34 last blocks can be ignored
            if size == size_title and idx_block < (len(text_blocks)-34):
                building = True
                # If the first letter of the title block is uppercase, new title
                if first_text[0] == first_text[0].upper():
                    if title:
                        title = FWords.adj_title(title)
                        titles.append(title)
                        years.append(year)

                    title = ""
                    year = "????"
                    cont_art += 1

                for idx_line, line in enumerate(block['lines']):
                    if idx_line > 0:
                        title += ' '
                    for idx_span, span in enumerate(line['spans']):
                        # text = span['text'].strip()
                        # title += ' ' + text + ' '
                        text = span['text']  # .strip()
                        title += text  # if text else ' '

            # To get the year (among Authors and Metadata)
            elif size == size_meta and building:
                year_candidate = last_text
                year_match = re.search(r'\b(19|20)\d{2}\b', year_candidate)
                year = year_match.group(0) if year_match else year

        # Append the last title
        if title:
            title = FWords.adj_title(title)
            titles.append(" ".join(title.split()))
            years.append(year)

    assert len(titles) == len(years)
    print(f"SS{ss_num}: {len(titles)} papers")

    # Print the titles found
    # for idx, t in enumerate(titles):
    #    print(f"{idx+1:03d}: {years[idx]} {t}")

    # Join the lists years and titles as a string separated by ";"
    articles = [f"{db};{year};{title}" for db, year,
                title in zip([f"SemSch{ss_num}"] * len(titles), years, titles)]
    results += articles


with open(f"{DIR_DATA_OUT}/SemanticScholar.csv", "w",
          encoding='utf-8') as file:
    for article in results:
        x = file.write(f"{article}\n")
