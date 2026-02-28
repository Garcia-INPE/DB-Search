import os
import fitz  # PyMuPDF
import importlib
import FunColors as FCol  # Custom module for color conversions
os.chdir("/home/jrmgarcia/ProjDocs/WFSP/Src_Python")
importlib.reload(FCol)

DIR_DATA = '/home/jrmgarcia/ProjDocs/WFSP/GoogleSearch_primary'
DOC = fitz.open(
    "/home/jrmgarcia/ProjDocs/WFSP/GoogleSearch_primary/Pages_01-20.pdf")

# The script CheckPDFColor.py helped to identify the green color used in the PDF
#    generated from the Google Scholar search
target_color_dec = FCol.rgb01_to_decimal((0, 0.5019607843137255, 0.0))
extracted_text = []
#

# Iterate through the pages (here we just use the first page)
for page_num in range(len(DOC)):

    page = DOC.load_page(page_num)  # Load the pages by index (0-based)
    text_blocks = page.get_text("dict")["blocks"]

    for block in text_blocks:
        if block['type'] == 0:  # 0 indicates a text block
            for line in block['lines']:
                for span in line['spans']:
                    # PyMuPDF stores color as an integer; convert it to an RGB tuple
                    span_color_dec = span['color']
                    # print(span['text'], span_color_dec)

                    if span_color_dec == target_color_dec:
                        extracted_text.append(
                            span['text'].replace('\n', '').replace('\xa0', ' '))

print(len(extracted_text))
#
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
