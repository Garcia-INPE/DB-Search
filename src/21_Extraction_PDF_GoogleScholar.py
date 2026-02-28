import os
import re
import fitz  # PyMuPDF
import FunWords as FWords

DIR_DATA_IN = '/home/jrmgarcia/ProjDocs/DB_Search/src/datain/PDF/GoogleScholar'
DIR_DATA_OUT = '/home/jrmgarcia/ProjDocs/DB_Search/src/dataout'

# Get the names of all PDF files in the input directory
all_pdf_files = sorted([f for f in os.listdir(
    DIR_DATA_IN) if f.endswith('.pdf')])

# Iterate among PDF files in the input directory
idx_file = 0
pdf = all_pdf_files[idx_file]
contTitle = contMeta = 0

titles = []
years = []

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
                color = block['lines'][0]['spans'][0]['color']

                if size == 12:
                    title = ""
                    # idx_lines=0; lines=block['lines]
                    for idx_line, line in enumerate(block['lines']):
                        # idx_span=0; span=lines['spans']
                        if idx_line > 0:
                            title += ' '
                        for idx_span, span in enumerate(line['spans']):
                            text = span['text']  # .strip()
                            # title += ' ' + text + ' '
                            title += text

                    title = FWords.adj_title(title)
                    titles.append(title)
                    contTitle += 1

                if color == 32768:
                    metadata = ""
                    # idx_lines=0; lines=block['lines]
                    for idx_line, line in enumerate(block['lines']):
                        # idx_span=0; span=lines['spans']
                        for idx_span, span in enumerate(line['spans']):
                            if span['color'] == 32768:
                                metadata += span['text']
                    all_dates = re.findall(r'\b(?:19|20)\d{2}\b', metadata)
                    year = all_dates[-1].strip() if all_dates else "????"
                    years.append(year)
                    contMeta += 1

                    # print(idx_file, idx_page, idx_block, " s:", size, "c:", color)

assert len(titles) == len(years) == 200

articles = [f"{db};{year};{title}" for db, year,
            title in zip(["GooSch"] * len(titles), years, titles)]

# At the end save all results to a CSV file
with open(f"{DIR_DATA_OUT}/GoogleScholar.csv", "w",
          encoding='utf-8') as file:
    for article in articles:
        x = file.write(f"{article}\n")
