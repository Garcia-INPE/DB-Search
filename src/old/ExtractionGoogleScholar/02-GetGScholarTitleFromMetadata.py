DIR_DATA = '/home/jrmgarcia/ProjDocs/DB_Search/datain/PrimarySearch_GoogleScholar'
fname_results = f'{DIR_DATA}/Pages_01-20.txt'
fname_meta = f'{DIR_DATA}/Pages_01-20_00-Metadata.txt'

# Read fname_results to a list
with open(fname_results, 'r', encoding='utf8') as f:
    lines_res = f.readlines()
# Replace '\n' with ''
lines_res = [line.replace('\n', '') for line in lines_res]

# Read fname_meta to a list
with open(fname_meta, 'r', encoding='utf8') as f:
    lines_meta = f.readlines()
# Replace '\n' with ''
lines_meta = [line.replace('\n', '') for line in lines_meta]
#


# For each line in lines_meta, get the index of the line in lines_res and feed
# a new list with the previous lines that are not blank
titles = []
line = lines_meta[0]
for line in lines_meta:
    if line in lines_res:
        idx = lines_res.index(line)
        # Get the previous non-blank line
        # i = idx-2
        for i in range(idx-1, -1, -1):
            if not lines_res[i]:
                break
        titles.append(" ".join(lines_res[i+1:idx]))

print("Metadata........:", len(lines_meta))
print("Titles..........:", len(titles))
#

# Assert that the length of titles is the same as lines_meta
assert len(titles) == len(lines_meta)

# Iterate over titles and lines_meta and create a new list in which each element is the year
# extracted from the corresponding element in lines_meta, followed by the corresponding
# element in titles, separated by a hyfen
titles_with_year = []
na_count = 0
for i, title in enumerate(titles):
    line_meta = lines_meta[i]
    # Pattern to extract year
    PATT_YEAR = r'\b(19|20)\d{2}\b'
    import re
    match = re.search(PATT_YEAR, line_meta)
    if match:
        year = match.group(0)
    else:
        na_count += 1
        year = 'N/A'

    titles_with_year.append(f"{year};{title}")

print("Titles with year:", len(titles_with_year))
print("N/A year values.:", na_count)
#

# Sort titles_with_year
titles_with_year.sort()


# Write titles_with_year to a file
fname_out = f'{DIR_DATA}/Pages_01-20_01-TitlesWithYear.txt'
with open(fname_out, 'w', encoding='utf8') as f:
    for line in titles_with_year:
        f.write(line + '\n')
print(f"Titles with year written to {fname_out}")
#

#
# After all work ome titles must be manually corrected
# For example, those that have "N/A" as year
# or those that have incorrect titles
# or removing duplicated entries with:
#    cat Pages_01-20_01-TitlesWithYear_OK.txt | sort | uniq
# The corrected titles are stored in a file with _final suffix
