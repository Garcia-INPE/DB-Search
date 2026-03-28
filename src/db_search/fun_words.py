import re
import string
import unicodedata
from typing import Iterable


_UNICODE_REPLACEMENTS = str.maketrans(
    {
        "“": '"',
        "”": '"',
        "„": '"',
        "‟": '"',
        "’": "'",
        "‘": "'",
        "‚": "'",
        "‛": "'",
        "‐": "-",
        "‑": "-",
        "‒": "-",
        "–": "-",
        "—": "-",
        "−": "-",
        "‾": "-",
        "⁄": "/",
        "∕": "/",
        "·": ".",
        "…": "...",
        "«": '"',
        "»": '"',
        "´": "'",
        "`": "'",
        "\n": " ",
        "\r": " ",
        "\f": " ",
        "\t": " ",
        "\u00a0": " ",
        "\u2007": " ",
        "\u202f": " ",
        "\u200b": "",
        "\ufeff": "",
        ";": "-",
    }
)

_PUNCTUATION_TO_SPACE = str.maketrans({char: " " for char in string.punctuation})
_WHITESPACE_RE = re.compile(r"\s+")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.:;!?\)])")
_SPACE_AFTER_OPEN_RE = re.compile(r"([\(\[])\s+")
_DASH_SPACE_RE = re.compile(r"\s*-\s*")
_MULTI_DOT_RE = re.compile(r"\.{2,}")
_MULTI_COLON_RE = re.compile(r":{2,}")
_MULTI_HYPHEN_RE = re.compile(r"-{2,}")

_DB_PREFIXES = {
    "ACM": "ACM_DL",
    "GOOGLESCHOLAR": "SCHOLA",
    "IEEE": "IEEE_X",
    "SCIENCEDIRECT": "SC_DIR",
    "SEMANTICSCHOLAR": "SEMAN",
    "SCOPUS": "SCOPUS",
    "SPRINGER": "SPRING",
    "TAYLOR": "TAYFRA",
    "WILEY": "WILEYL",
}


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def normalize_text(text: str, strip_accents: bool = True) -> str:
    if text is None:
        return ""

    normalized = unicodedata.normalize("NFKC", str(text)).translate(_UNICODE_REPLACEMENTS)
    if strip_accents:
        normalized = _strip_accents(normalized)
    return normalized


def adj_title(txt, del_quotes: bool = False, strip_accents: bool = True):
    ret = normalize_text(txt, strip_accents=strip_accents).strip('"\' ')
    ret = _WHITESPACE_RE.sub(" ", ret)
    ret = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", ret)
    ret = _SPACE_AFTER_OPEN_RE.sub(r"\1", ret)
    ret = _DASH_SPACE_RE.sub("-", ret)
    ret = _MULTI_DOT_RE.sub(".", ret)
    ret = _MULTI_COLON_RE.sub(":", ret)
    ret = _MULTI_HYPHEN_RE.sub("-", ret)
    ret = ret.replace(" ,", ",").replace(" .", ".").replace(" :", ":")
    ret = ret.replace("for for", "for")
    ret = ret.rstrip(".")
    if del_quotes:
        ret = ret.replace('"', "").replace("'", "")
    return ret.strip()


def adj_title_array(aTitles: Iterable, del_quotes: bool = False, strip_accents: bool = True):
    return [adj_title(title, del_quotes=del_quotes, strip_accents=strip_accents) for title in aTitles]


def clean_word(word, strip_accents: bool = True):
    normalized = normalize_text(word, strip_accents=strip_accents)
    cleaned = normalized.translate(_PUNCTUATION_TO_SPACE)
    return _WHITESPACE_RE.sub(" ", cleaned).strip()


def get_db_name(fname):
    db_name = str(fname).lstrip().upper()
    for prefix, canonical_name in _DB_PREFIXES.items():
        if db_name.startswith(prefix):
            return canonical_name
    return db_name