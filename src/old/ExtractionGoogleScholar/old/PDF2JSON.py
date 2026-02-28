import PyPDF2
import json
import re


def preprocess_pdf_text(pdf_path):
    # pdf_path = "docs/2022-Wu+ Simulation of forest fire spread based on AI-ELSEVIER.pdf"
    """Preprocesses PDF text, removing headers, footers, converting tables to text, and handling special characters."""

    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        pages = []
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            page_text = page.extract_text()

            # 1. Remove headers and footers
            lines = page_text.splitlines()
            # Remove the first 2 and last 2 lines
            page_text = "\n".join(lines)
            
            # 2. Convert tables to text
            # Replace "|" with spaces
            page_text = re.sub(r'\|', ' ', page_text)
            page_text = re.sub(r'\s+', ' ', page_text)  # Remove extra spaces

            # 3. Handle special characters
            # Replace en dash with hyphen
            page_text = page_text.replace('–', '-')
            # Replace ellipsis with "..."
            page_text = page_text.replace('…', '...')

            pages.append({"page": page_num + 1, "text": page_text})

    return {"filename": pdf_path, "content": pages}


def extract_text_to_json(pdf_path):
    """Extracts text from a PDF, preprocesses it, and stores it in a JSON file."""

    json_data = preprocess_pdf_text(pdf_path)

    with open("PDF2.json", "w") as f:
        json.dump(json_data, f, indent=4)


# Example usage:
extract_text_to_json(
    "docs/2023-Integrated Geomatics and RS Analysis of Forest Fire Propagation and land Cover Change-EEET.pdf")
