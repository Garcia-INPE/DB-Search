import os
import sys
import importlib
import fitz  # PyMuPDF
from pathlib import Path

FILE_DIR = Path(__file__).resolve().parent
SRC_DIR = next((p for p in [FILE_DIR, *FILE_DIR.parents] if p.name == 'src'), FILE_DIR)
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from db_search import fun_colors as FCol
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
page_num = 0
for page_num in range(len(DOC)):
    page = DOC.load_page(page_num)  # Load the pages by index (0-based)
    text_blocks = page.get_text("dict")["blocks"]
    block = text_blocks[0]
    for block in text_blocks:
        if block['type'] == 0:  # 0 indicates a text block
            line = block['lines'][0]
            for line in block['lines']:
                span = line['spans'][0]
                for span in line['spans']:
                    # PyMuPDF stores color as an integer; convert it to an RGB tuple
                    span_color_dec = span['color']
                    # Store unique colors found in decimal format
                    span_color_set_dec.add(span_color_dec)

                    if not check_color_only:
                        if span_color_dec == target_color_dec:
                            extracted_text.append(
                                span['text'].replace('\n', '').replace('\xa0', ' '))

# sort the set span_color_set
span_color_set_dec = sorted(list(span_color_set_dec))

if check_color_only:
    # colors = [FCol.rgb255_to_rgb01(FCol.decimal_to_rgb255(x))
    #          for x in span_color_set_dec]
    # Print each color with its RGB 0-255, RGB 0-1, hexadecimal and decimal representations
    for idx, color_dec in enumerate(sorted(span_color_set_dec)):
        rgb255 = FCol.decimal_to_rgb255(color_dec)
        text = f"Color {idx}:  DEC:{color_dec}  RGB255:{rgb255}  HEX:{FCol.rgb255_to_hex(FCol.decimal_to_rgb255(color_dec))}  RGB01: {FCol.rgb255_to_rgb01(FCol.decimal_to_rgb255(color_dec))}"
        FCol.print_rgb_background(text, rgb255[0], rgb255[1], rgb255[2])


else:
    iText = 0
    while iText < (len(extracted_text)-1):
        if extracted_text[iText].endswith(' ') or \
            extracted_text[iText+1].startswith(',') or \
                extracted_text[iText+1].startswith(' '):
            extracted_text[iText] += extracted_text[iText+1]
            del extracted_text[iText+1]
        else:
            # Only increment i if no line join was made
            iText += 1

    for i, line in enumerate(extracted_text):
        print(f"{i+1:03d}: {line}")
    print("Total of papers:", len(extracted_text))
    #

    # Save the metadata to a text file
    fname_meta = f'{DIR_DATA}/Pages_01-20_00-Metadata.txt'
    with open(fname_meta, 'w', encoding='utf-8') as f:
        for line in extracted_text:
            f.write(line + "\n")
    print(f"{os.path.basename(fname_meta)} successfully created!")

    type(extracted_text)
    #
