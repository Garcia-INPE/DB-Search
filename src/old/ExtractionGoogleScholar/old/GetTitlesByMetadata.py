#
# The metadata used was the authors and the year of publication.
# but now every paper contains it

import re
import os
DIR_WORK = '/home/jrmgarcia/ProjDocs/WFSP/GoogleSearch_primary'

# Read the lines from the two TXT files
with open(f'{DIR_WORK}/Pages_01-20.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()
print(len(lines))
#

# Find out the indexes of lines contain the text: "Risk Estimation"
# [i for i, line in enumerate(lines) if "Risk Estimation" in line]


# Show lines that contain the year of each paper
meta = []
titles = []
dates = []
PATT_DT = r'\b(19|20)\d{2}\b'
# PATT = r'.* - .*,? ?' + PATT_DT + ' - .*$'
# PATT = r'.* - .*, ' + PATT_DT + ' - .*$'
PATT = r'.* ' + PATT_DT + ' - .*$'
for i, line in enumerate(lines):
    if re.search(PATT, lines[i]):
        print(True)
        # Get the date from the line using regular expression
        dates.append(re.search(PATT_DT, lines[i]).group(0))
        meta.append(lines[i])
        titles.append(lines[i-2])
        titles.append(lines[i-1])
print('1) T:', len(titles), '  D:', len(dates), '  M:', len(meta))
#

# Delete empty lines from titles
titles = [title for title in titles if title.strip() != '']
print('2) T:', len(titles), '  D:', len(dates), '  M:', len(meta))
#

# Joins lines that start with a lowercase letter to the previous line
for i in range(1, len(titles)):
    if titles[i] and titles[i].strip()[0].islower():
        titles[i-1] = titles[i-1].replace("\n", "") + ' ' + titles[i]
        titles[i] = ''
print('3) T:', len(titles), '  D:', len(dates), '  M:', len(meta))
#

# Delete empty lines from titles
titles = [title for title in titles if title.strip() != '']
print('4) T:', len(titles), '  D:', len(dates), '  M:', len(meta))
#

# Delete lines that are exactly equal to certain strings
out_equals = ["View all", "Save", "Cite", "1/2", "2/2"]
titles = [title for title in titles if title not in out_equals]
print('5) T:', len(titles), '  D:', len(dates), '  M:', len(meta))
#

# Delete lines that contain "All" and "versions"
titles = [title for title in titles if "All" not in title and "versions" not in title]
print('6) T:', len(titles), '  D:', len(dates), '  M:', len(meta))
#

# Delete lines that contain certain substrings
out_in = ["Cited by ", "(survey OR review) ", " PM", "…",
          ".org", ".com", ".net", ".gov", ".edu",
          "Journal", "Springer", "Elsevier", "CSIRO", "Wiley",
          "Taylor & Francis"]
titles = [title for title in titles if not any(sub in title for sub in out_in)]
print('7) T:', len(titles), '  D:', len(dates), '  M:', len(meta))
#

# Save the titles
fname_titles = f'{DIR_WORK}/Pages_01-20_00-Titles.txt'
with open(fname_titles, 'w', encoding='utf-8') as f:
    for line in titles:
        f.write(line)
print(f"{os.path.basename(fname_titles)} successfully created!")
#

#
print("\nAQUI OS TÍTULOS FORAM GERADOS, PORÉM É PRECISO HAVER UMA INTERVENÇAO MANUAL")
print("PARA UNIR LINHAS QUE FORAM MATIDAS SEPARADAS, ATÉ QUE A QTD DE TITLES = QTD DE DATES.")
print('7) T:', len(titles), '  D:', len(dates), '  M:', len(meta))
#

# Save the dates
fname_dates = f'{DIR_WORK}/Pages_01-20_00-Dates.txt'
with open(fname_dates, 'w', encoding='utf-8') as f:
    for line in dates:
        f.write(line)
print(f"{os.path.basename(fname_dates)} successfully created!")
#
