import sys
from pathlib import Path
from typing import Optional


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