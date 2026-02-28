# The first 20 pages from a Google Scholar search result were saved into PDF files,
# which were then joined together in one PDF file using the pdfunite Linux/Ubuntu tool.
# The text were extracted using the pdftotext Linux/Ubuntu tool int a TXT file.
#
# This Python script reads this TXT file, processes it, and generates a TXT file
# containing only the titles of the articles, as clean as possible.
# By process, we meant to eliminate lines that are certainly not titles, based on certain markers.
# Aborted:

import os
DIR_WORK = '/home/jrmgarcia/ProjDocs/WFSP/GoogleSearch_primary'

# Read the lines from the two TXT files
with open(f'{DIR_WORK}/Pages_01-20.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()
print(len(lines))
#

# Replace all new line characters with empty strings
lines = [line.replace('\n', '') for line in lines]
print(len(lines))
#

# Delete empty lines and lines with only whitespace
lines = [line for line in lines if line != "\n" and line != ""]
print(len(lines))
#

# Delete lines that are exactly equal to certain strings
out_equals = ["View all", "Save", "Cite", "1/2", "2/2"]
lines = [line for line in lines if line not in out_equals]
print(len(lines))
#

# Delete lines that contain certain substrings
out_in = ["Cited by ", " PM",]
lines = [line for line in lines if not any(sub in line for sub in out_in)]
print(len(lines))

# Save the cleaned lines to a new intermediate file
fname_filtered = f'{DIR_WORK}/Pages_01-20_01-Filtered.txt'
with open(fname_filtered, 'w', encoding='utf-8') as f:
    for line in lines:
        f.write(line + '\n')
print(f"{os.path.basename(fname_filtered)} successfully created!")

lines_filtered = []
# Iterate through the lines and add to another list the two lines following the lines that contain any item from markers
# if the next line does not contain any item from markers
markers = ["(survey", "All", "versions", "Related articles", "https"]
for i in range(len(lines)-1):
    if (any(marker in lines[i] for marker in markers) and not any(marker in lines[i+1] for marker in markers)) and \
            i+2 < len(lines):
        lines_filtered.append(lines[i+1])
        lines_filtered.append(lines[i+2])
print(len(lines_filtered))
#

# Save the cleaned lines to a new file after filtering with markers
fname_cleaned1 = f'{DIR_WORK}/Pages_01-20_02-Cleaned-1.txt'
with open(fname_cleaned1, 'w', encoding='utf-8') as f:
    for line in lines_filtered:
        f.write(line + '\n')
print(f"{os.path.basename(fname_cleaned1)} successfully created!")
#

# Apply some more filters
lines = lines_filtered

# Delete lines that contain "All" and "versions"
lines = [linha for linha in lines if "All" not in linha and "versions" not in linha]
print(len(lines))

# Delete lines that contain certain substrings
out_in = ["Cited by ", "(survey OR review) ", " PM", "…",
          ".org", ".com", ".net", ".gov", ".edu",
          "Journal", "Springer", "Elsevier", "CSIRO", "Wiley",
          "Taylor & Francis"]
lines = [linha for linha in lines if not any(sub in linha for sub in out_in)]
print(len(lines))
#

# Joins lines that start with a lowercase letter to the previous line
for i in range(1, len(lines)):
    if lines[i] and lines[i][0].islower():
        lines[i-1] += ' ' + lines[i]
        lines[i] = ''
# Delete empty lines and lines with only whitespace again
lines = [line for line in lines if line != "\n" and line != ""]
# lines = [linha.strip() for linha in lines if linha.strip()]
print(len(lines))

# Save the cleaned lines to a new file after applying other filters
fname_cleaned2 = f'{DIR_WORK}/Pages_01-20_03-Cleaned-2.txt'
with open(fname_cleaned2, 'w', encoding='utf-8') as f:
    for line in lines_filtered:
        f.write(line + '\n')
print(f"{os.path.basename(fname_cleaned2)} successfully created!")
#

# Sort lines alphabetically
# lines = sorted(lines)

# Keep only unique lines
# lines = list(dict.fromkeys(lines))
# print(len(lines))

# Save the cleaned lines to a new file
fname_sort_uniq = f'{DIR_WORK}/Pages_01-20_04-Sort_Uniq.txt'
with open(fname_sort_uniq, 'w', encoding='utf-8') as f:
    for line in lines:
        f.write(line + '\n')
print(f"{os.path.basename(fname_sort_uniq)} successfully created!")
#
