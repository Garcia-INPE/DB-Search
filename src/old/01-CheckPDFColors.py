from rich import print as rprint
import pdfplumber
import FunColors as FCol

set_stroke_color = set()
set_fill_color = set()

pdf_path = "/home/jrmgarcia/ProjDocs/DB_Search/datain/PrimarySearch_GoogleScholar/Pages_01-20.pdf"

with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        for char in page.chars:
            # Print color attributes for inspection
            if char.get('non_stroking_color'):
                set_fill_color.add(char['non_stroking_color'])
                # print(
                #    f"Character: {char['text']}, Fill Color: {char['non_stroking_color']}")
            if char.get('stroking_color'):
                set_stroke_color.add(char['stroking_color'])
                #    f"Character: {char['text']}, Stroke Color: {char['stroking_color']}")

# Show unique colors found, ordered
print("Unique Fill Colors (non-stroking):", sorted(set_fill_color))
print("Unique Stroke Colors (stroking):", sorted(set_stroke_color))

# rprint("[rgb(0,0,255)]This text is in blue color[/]")
for stroke_color in set_stroke_color:
    # remove blank spaces from stroke_color if any
    rgb255 = str(FCol.rgb_to_255(stroke_color)).replace(" ", "")
    rprint(f"[rgb{rgb255}]{stroke_color} {rgb255}[/]")
