import os
import re
import sys
from pathlib import Path
import importlib
import fitz  # PyMuPDF

# Interactive execution from the project root needs src added before package imports.
if "__file__" not in globals():
    sys.path.insert(0, str(Path.cwd() / "src"))

from db_search import fun_colors as FCol
from db_search.paths import DATA_IN_DIR, DATA_OUT_DIR, ensure_src_on_path

ensure_src_on_path(__file__ if "__file__" in globals() else None)
importlib.reload(FCol)

DIR_DATA_IN = DATA_IN_DIR / 'PDF' / 'GoogleScholar' / 'Pages'
DIR_DATA_OUT = DATA_OUT_DIR

# Get the names of all PDF files in the input directory
all_pdf_files = sorted([f for f in os.listdir(
    DIR_DATA_IN) if f.endswith('.pdf')])

# Iterate among PDF files in the input directory
idx_file = 0
pdf = all_pdf_files[idx_file]
cont = 0
for idx_file, pdf in enumerate(all_pdf_files):
    file_path = os.path.join(DIR_DATA_IN, pdf)
    DOC = fitz.open(file_path)

    # if idx_file > 0:
    #    break

    # Iterate all pages of the PDF file
    # idx_page=0; page=DOC.load_page(idx_page)
    for idx_page, page in enumerate(DOC):
        page_blocks = page.get_text("dict")["blocks"]
        # idx_block = 0; block=text_blocks[idx_block]
        for idx_block, block in enumerate(page_blocks):
            if block['type'] == 0:   # text block
                size = block['lines'][0]['spans'][0]['size']
                first_text = block['lines'][0]['spans'][0]['text']
                font = block['lines'][0]['spans'][0]['font']
                last_text = block['lines'][-1]['spans'][-1]['text']
                color = block['lines'][0]['spans'][0]['color']
                flags = block['lines'][0]['spans'][0]['flags']
                char_flags = block['lines'][0]['spans'][0]['char_flags']
                if size == 12:
                    print(idx_file, idx_page, idx_block, " s:", size, "c:", color,
                          " ft:", first_text, " lt:", last_text, " f:", font, " fg:", flags, " cf:", char_flags)
                    cont += 1
                year_match = re.search(r'\b(19|20)\d{2}\b', last_text)
                # if color == 32768:
                # cont += 1


print("qtd =", cont)
