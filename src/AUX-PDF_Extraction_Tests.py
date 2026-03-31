import os
import re
import sys
from pathlib import Path
import importlib
import fitz  # PyMuPDF

from db_search import fun_colors as FCol
from db_search.paths import DATA_IN_DIR, DATA_OUT_DIR
importlib.reload(FCol)
DIR_IN = Path(DATA_IN_DIR / "SS01" / "PDF" / "SemanticScholar" / "manual")
DIR_OUT = Path(DATA_OUT_DIR / "SS01")

all_pdf_files = sorted([f for f in os.listdir(DIR_IN) if f.endswith('.pdf')])

# Iterate among PDF files in the input directory
# idx_file = 0; pdf = all_pdf_files[idx_file]
cont = 0
for idx_file, pdf in enumerate(all_pdf_files):
    file_path = os.path.join(DIR_IN, pdf)
    DOC = fitz.open(file_path)

    # if idx_file > 0:
    #    break

    # Iterate all pages of the PDF file
    # idx_page=0; page=DOC.load_page(idx_page)
    for idx_page, page in enumerate(DOC):
        page_blocks = page.get_text("dict")["blocks"]
        # idx_block = 5; block=page_blocks[idx_block]
        for idx_block, block in enumerate(page_blocks):
            if block['type'] == 0:   # text block
                size = block['lines'][0]['spans'][0]['size']
                first_text = block['lines'][0]['spans'][0]['text']
                font = block['lines'][0]['spans'][0]['font']
                last_text = block['lines'][-1]['spans'][-1]['text']
                color = block['lines'][0]['spans'][0]['color']
                flags = block['lines'][0]['spans'][0]['flags']
                char_flags = block['lines'][0]['spans'][0]['char_flags']
                if idx_block <= 0:
                   print(last_text)
                   stop()

                if size == 12:
                    print(idx_file, idx_page, idx_block, " s:", size, "c:", color,
                          " ft:", first_text, " lt:", last_text, " f:", font, " fg:", flags, " cf:", char_flags)
                    cont += 1
                year_match = re.search(r'\b(19|20)\d{2}\b', last_text)
                # if color == 32768:
                # cont += 1


print("qtd =", cont)
