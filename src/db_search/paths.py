import sys
from typing import Optional
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
DATA_IN_DIR = SRC_DIR / "datain"
DATA_OUT_DIR = SRC_DIR / "dataout"
LOGS_DIR = DATA_OUT_DIR / "logs"
GOOGLE_SCHOLAR_LOG_DIR = LOGS_DIR / "GoogleScholar"
SEMANTIC_SCHOLAR_LOG_DIR = LOGS_DIR / "SemanticScholar"
PROJECT_ROOT = SRC_DIR.parent


def ensure_src_on_path(file_hint: Optional[str] = None) -> Path:
	"""Ensure the nearest src directory is available on sys.path."""
	if file_hint:
		start_dir = Path(file_hint).resolve().parent
	else:
		cwd = Path.cwd().resolve()
		start_dir = cwd / "src" if (cwd / "src").is_dir() else cwd

	src_dir = next(
		(p for p in [start_dir, *start_dir.parents] if p.name == "src"),
		SRC_DIR,
	)

	if str(src_dir) not in sys.path:
		sys.path.insert(0, str(src_dir))

	return src_dir
