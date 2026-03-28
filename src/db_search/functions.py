import sys
from pathlib import Path
from typing import Optional


DB_PREFIXES = {
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

DB_LABELS = {
    "ACM_DL": "ACM DL",
    "SCHOLA": "Google Scholar",
    "IEEE_X": "IEEE Xplorer",
    "SC_DIR": "Science Direct",
    "SEMAN": "Semantic Scholar",
    "SCOPUS": "SCOPUS",
    "SPRING": "Springer Nature",
    "TAYFRA": "Taylor & Francis",
    "WILEYL": "Wiley",
}


def ensure_src_on_path(file_hint: Optional[str] = None) -> Path:
    """Ensure the nearest src directory is available on sys.path."""
    if file_hint:
        start_dir = Path(file_hint).resolve().parent
    else:
        cwd = Path.cwd().resolve()
        start_dir = cwd / "src" if (cwd / "src").is_dir() else cwd

    src_dir = next(
        (p for p in [start_dir, *start_dir.parents] if p.name == "src"),
        start_dir,
    )

    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    return src_dir


def get_db_name(fname: str) -> str:
    """Map a source filename prefix to a canonical DB code."""
    db_name = str(fname).lstrip().upper()
    for prefix, canonical_name in DB_PREFIXES.items():
        if db_name.startswith(prefix):
            return canonical_name
    return db_name


def get_db_label(db_code: str) -> str:
    """Map canonical DB code to a chart-friendly label."""
    code = "" if db_code is None else str(db_code).strip()
    if not code:
        return ""

    # Exact canonical code
    if code in DB_LABELS:
        return DB_LABELS[code]

    # Prefix variants, e.g. SEMAN1..SEMAN9
    for prefix, label in DB_LABELS.items():
        if code.startswith(prefix):
            return f"{label} ({code})"

    return code