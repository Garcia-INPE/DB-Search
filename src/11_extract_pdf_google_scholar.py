import os
import re
import sys
from html import unescape
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import Request, urlopen

import fitz  # PyMuPDF


TRUNCATION_PREFIX_RE = re.compile(r"^\s*(?:\.\.\.|…)\s*[:;\-–—]*\s*")
TITLE_META_PATTERNS = [
    re.compile(r'<meta[^>]+name=["\']citation_title["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<meta[^>]+name=["\']dc\.title["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<title[^>]*>(.*?)</title>', re.IGNORECASE | re.DOTALL),
]

# Interactive execution from the project root needs src added before package imports.
if "__file__" not in globals():
    sys.path.insert(0, str(Path.cwd() / "src"))

from db_search import fun_words as FWords
from db_search.paths import DATA_IN_DIR, DATA_OUT_DIR, ensure_src_on_path

ensure_src_on_path(__file__ if "__file__" in globals() else None)

DIR_DATA_IN = DATA_IN_DIR / 'PDF' / 'GoogleScholar'
DIR_DATA_OUT = DATA_OUT_DIR

# Support both layouts:
# 1) src/datain/PDF/GoogleScholar/*.pdf
# 2) src/datain/PDF/GoogleScholar-*.pdf
if DIR_DATA_IN.is_dir():
    all_pdf_files = sorted([f for f in os.listdir(DIR_DATA_IN) if f.endswith('.pdf')])
    pdf_base_dir = DIR_DATA_IN
else:
    pdf_base_dir = DATA_IN_DIR / 'PDF'
    all_pdf_files = sorted([
        f for f in os.listdir(pdf_base_dir)
        if f.endswith('.pdf') and f.startswith('GoogleScholar')
    ])

# Iterate among PDF files in the input directory
idx_file = 0
pdf = all_pdf_files[idx_file]
contTitle = contMeta = 0

titles = []
years = []
truncated_title_rows = []
resolved_title_cache = {}


def strip_google_scholar_truncation_prefix(title: str) -> str:
    """Remove common Google Scholar truncation markers from title starts."""
    return TRUNCATION_PREFIX_RE.sub("", title).strip()


def get_block_uri(block, page_links):
    rect = fitz.Rect(block['bbox'])
    uris = []
    for link in page_links:
        uri = link.get('uri')
        if not uri or uri.startswith('javascript:'):
            continue
        link_rect = link.get('from')
        if not link_rect:
            continue
        if rect.intersects(link_rect):
            uris.append(uri)
    return next(iter(dict.fromkeys(uris)), None)


def normalize_article_url(url: str | None) -> str | None:
    if not url:
        return None

    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    redirect_url = params.get('redirect_uri')
    if redirect_url:
        return unquote(redirect_url[0])
    return url


def fetch_title_from_url(url: str | None) -> str | None:
    normalized_url = normalize_article_url(url)
    if not normalized_url:
        return None
    if normalized_url in resolved_title_cache:
        return resolved_title_cache[normalized_url]

    try:
        request = Request(normalized_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(request, timeout=15) as response:
            raw_html = response.read(512_000)
            encoding = response.headers.get_content_charset() or 'utf-8'
        html = raw_html.decode(encoding, errors='ignore')
    except Exception:
        resolved_title_cache[normalized_url] = None
        return None

    for pattern in TITLE_META_PATTERNS:
        match = pattern.search(html)
        if match:
            candidate = unescape(match.group(1))
            candidate = re.sub(r'\s+', ' ', candidate).strip()
            if candidate:
                cleaned = FWords.adj_title(candidate)
                resolved_title_cache[normalized_url] = cleaned
                return cleaned

    resolved_title_cache[normalized_url] = None
    return None

for idx_file, pdf in enumerate(all_pdf_files):
    file_path = os.path.join(pdf_base_dir, pdf)
    DOC = fitz.open(file_path)

    # if idx_file > 0:
    #    break

    # Iterate all pages of the PDF file
    # idx_page=0; page=DOC.load_page(idx_page)
    for idx_page, page in enumerate(DOC):
        page_blocks = page.get_text("dict")["blocks"]
        page_links = page.get_links()
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
                    title_url = get_block_uri(block, page_links)
                    cleaned_title = strip_google_scholar_truncation_prefix(title)
                    resolved_title = None
                    if cleaned_title != title:
                        resolved_title = fetch_title_from_url(title_url)
                    if resolved_title:
                        cleaned_title = resolved_title
                    if cleaned_title != title:
                        truncated_title_rows.append((idx_file, idx_page, title, cleaned_title, title_url))
                    title = cleaned_title
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
            title in zip(["SCHOLA"] * len(titles), years, titles)]

# At the end save all results to a CSV file
with open(DIR_DATA_OUT / 'GoogleScholar.csv', "w",
          encoding='utf-8') as file:
    for article in articles:
        x = file.write(f"{article}\n")

if truncated_title_rows:
    with open(DIR_DATA_OUT / 'GoogleScholar_truncated_titles.log', 'w', encoding='utf-8') as file:
        for idx_file, idx_page, raw_title, cleaned_title, title_url in truncated_title_rows:
            file.write(
                f"file={idx_file} page={idx_page} | raw={raw_title} | cleaned={cleaned_title} | url={title_url}\n"
            )
