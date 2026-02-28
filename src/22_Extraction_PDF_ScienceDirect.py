import os
import re
import fitz  # PyMuPDF
import FunWords as FWords

DIR_DATA_IN = '/home/jrmgarcia/ProjDocs/DB_Search/src/datain/PDF/ScienceDirect_Elsevier'
DIR_DATA_OUT = '/home/jrmgarcia/ProjDocs/DB_Search/src/dataout'

results = []
# Loop among 24 search strings from Science Direct (due to it supports only 8 boolean operators in the search string)
ss_num = 1
for ss_num in range(1, 25):
    # Get the names of all PDF files in the input directory
    ss_num_str = f"{ss_num:02d}"
    all_pdf_files = sorted([f for f in os.listdir(
        DIR_DATA_IN) if f.startswith(f'S{ss_num_str}') and f.endswith('.pdf')])

    cont_art = 0
    titles = []
    years = []

    # if ss_num > 1:
    #     break

    # Iterate among PDF files in the input directory
    # idx_file = 0; pdf = all_pdf_files[idx_file]
    for idx_file, pdf in enumerate(all_pdf_files):
        file_path = os.path.join(DIR_DATA_IN, pdf)
        file_path = os.path.join(DIR_DATA_IN, "S02P1.pdf")
        DOC = fitz.open(file_path)

        # if idx_file > 0:
        #     break

        title = ""
        year = "????"
        building = False

        # if idx_file > 0:
        #    break

        # Titles are in blocks with size=12.0,          flags=0, char_flag=0, font=Unnamed-T3
        # Metadata (year) are in blocks with size=10.5, flags=4, char_flag=16, font=ElsevierSansWeb-Regular
        # Years are the last text of the metadata

        # Iterate all pages of the PDF file
        # idx_page=0; page=DOC.load_page(idx_page)
        for idx_page, page in enumerate(DOC):
            page_blocks = page.get_text("dict")["blocks"]
            last_title_block = -10

            # idx_block = 0; block=text_blocks[idx_block]
            for idx_block, block in enumerate(page_blocks):
                if block['type'] != 0:  # not a text block
                    continue

                size = block["lines"][0]['spans'][0]['size']
                font = block['lines'][0]['spans'][0]['font']
                flags = block['lines'][0]['spans'][0]['flags']
                char_flags = block['lines'][0]['spans'][0]['char_flags']
                first_text = block['lines'][0]['spans'][0]['text'].strip()
                last_text = block['lines'][-1]['spans'][-1]['text'].strip()

                # print(idx_file, idx_page, idx_block, " s:", size,
                #       " ft:", first_text, " lt:", last_text, " f:", font, " fg:", flags, " cf:", char_flags)

                # To get the title
                if size == 12.0 and flags == 0 and char_flags == 0 and font == "Unnamed-T3":
                    building = True
                    for idx_line, line in enumerate(block['lines']):
                        if idx_line > 0 or idx_block != last_title_block:
                            title += ' '
                        for idx_span, span in enumerate(line['spans']):
                            text = span['text']  # .strip()
                            # title += ' ' + text + ' '
                            title += text
                    last_title_block = idx_block

                # To get the year (among Authors and Metadata)
                elif size == 10.5 and building and flags == 4 and char_flags == 16 and font == "ElsevierSansWeb-Regular" and \
                        re.search(r'\b(19|20)\d{2}\b', last_text):
                    year_match = re.search(r'\b(19|20)\d{2}\b', last_text)
                    year = year_match.group(0) if year_match else year

                    if title:
                        title = FWords.adj_title(title)
                        titles.append(title)
                        years.append(year)

                        title = ""
                        year = "????"
                        cont_art += 1
                        building = False

        assert len(titles) == len(years)
        print(f"S{ss_num_str}: {len(titles)} papers")

        # Join the lists years and titles as a string separated by ";"
        articles = [f"{db};{year};{title}" for db, year,
                    title in zip([f"SciDir{ss_num_str}"] * len(titles), years, titles)]

        results += articles

    # [t for t in results if "Mathematical models and calculation" in t]

    # Print the articles found
    # for idx, a in enumerate(articles):
    #   print(f"{idx+1:03d}: {a}")


# At the end save all results to a CSV file
with open(f"{DIR_DATA_OUT}/ScienceDirect.csv", "w",
          encoding='utf-8') as file:
    for article in results:
        x = file.write(f"{article}\n")
