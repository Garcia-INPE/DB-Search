import os
import re
import sys
import importlib
import fitz  # PyMuPDF

# Add the parent directory to sys.path to import custom modules
current_dir = os.path.dirname(__name__)
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
if not parent_dir in sys.path:
    sys.path.append(parent_dir)

# Import the package FunColors from the parent directory
import FunColors as FCol  # Custom module for color conversions # nopep8
importlib.reload(FCol)

DIR_DATA_IN = '/home/jrmgarcia/ProjDocs/DB_Search/src/datain/PDF/GoogleScholar/Pages'
DIR_DATA_OUT = '/home/jrmgarcia/ProjDocs/DB_Search/src/dataout'

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
