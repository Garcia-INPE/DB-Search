import os
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


DIR_DATA = '/home/jrmgarcia/ProjDocs/DB_Search/src/datain/PDF'
DOC = fitz.open(f"{DIR_DATA}/Scopus_Document_search_results.pdf")

check_color_only = True
# Step 1) Use True to shows all colors found in the PDF in RGB 0-1 scale and choose the target color
# Step 2) Use False to extract text with the target color only

# Change the variable check_color_only iot identify or extract
# metadata from the PDF generated from Google Scholar search pages
# Change the target_color_dec variable to the desired color in decimal format
target_color_dec = 32768  # Because the span color is repported in decimal format
extracted_text = []
span_color_set_dec = set()

# Iterate through the pages (here we just use the first page)

page_num = 1
page = DOC.load_page(page_num)  # Load the pages by index (0-based)
# blocks: 26, 34
text_blocks = page.get_text("dict")["blocks"]
'''
idx_block=16; block=text_blocks[idx_block]
idx_line=0; line=block['lines'][idx_line]
idx_span=0; span=line['spans'][idx_span]
print(span, len(text_blocks), len(block['lines']), len(line['spans']))
for idx_block, block in enumerate(text_blocks):
    if block['type'] == 0:  # 0 indicates a text block
        for idx_line, line in enumerate(block['lines']):
            for idx_span, span in enumerate(line['spans']):
                if span['flags'] == 20 and span['char_flags'] == 24 and span['font'] == 'ElsevierSansWeb-Bold' and len(block['lines']) > 1:
                    print(idx_block, idx_line, idx_span, span['text'])
#
'''


titles = []
title = ""
# idx_page = 24; page = DOC.load_page(idx_page)


for idx_page, page in enumerate(DOC):
    text_blocks = page.get_text("dict")["blocks"]
    last_title_block = -10
    '''
    idx_block = 31; block = text_blocks[idx_block]
    idx_line = 0; line = block['lines'][idx_line]
    idx_span = 0; span = line['spans'][idx_span]
    '''
    for idx_block, block in enumerate(text_blocks):
        if block['type'] == 0:  # 0 indicates a text block
            for idx_line, line in enumerate(block['lines']):
                for idx_span, span in enumerate(line['spans']):
                    if span['flags'] == 20 and span['char_flags'] == 24 and span['font'] == 'ElsevierSansWeb-Bold' and len(block['lines']) > 1:

                        if idx_page == 24 and idx_block == 30 and idx_line == 2 and idx_span == 0:
                            x = span['xxx']

                        text = span['text']

                        # Start a new title if block index is neither current or previous
                        if idx_block in [last_title_block, last_title_block + 1]:
                            title += " " + text
                        else:
                            if title:
                                titles.append(" ".join(title.split()).strip())
                                title = text

                        last_title_block = idx_block

                        print(idx_page, idx_block,
                              idx_line, idx_span, text)

# titles
