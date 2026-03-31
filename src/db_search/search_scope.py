from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
import re

from db_search.paths import DATA_IN_DIR, DATA_OUT_DIR


SEARCH_STRINGS_FILENAME = "search_strings.csv"
LEGACY_CONFIG_FILENAME = "config.csv"


@dataclass(frozen=True)
class SearchScope:
    ss_id: int
    search_string: str
    config_path: Path


def _normalize_header(text: str) -> str:
    return "".join(ch for ch in text.strip().upper() if ch not in {" ", "_"})


def _extract_ss_id_from_scope_name(name: str) -> int:
    match = re.fullmatch(r"SS(\d+)", name.strip())
    if not match:
        return -1
    return int(match.group(1))


def resolve_config_path(config_csv: Path | None = None, ss_id: int | None = None) -> Path:
    if config_csv is not None:
        path = Path(config_csv).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Search-strings CSV not found: {path}")
        return path

    candidates: list[Path] = []
    if ss_id is not None:
        candidates.extend(
            [
                DATA_IN_DIR / f"SS{ss_id}" / "CSV" / SEARCH_STRINGS_FILENAME,
                DATA_IN_DIR / f"SS{ss_id:02d}" / "CSV" / SEARCH_STRINGS_FILENAME,
                DATA_IN_DIR / f"SS{ss_id}" / "CSV" / LEGACY_CONFIG_FILENAME,
                DATA_IN_DIR / f"SS{ss_id:02d}" / "CSV" / LEGACY_CONFIG_FILENAME,
            ]
        )

    candidates.extend([
        DATA_IN_DIR / SEARCH_STRINGS_FILENAME,
        DATA_IN_DIR / "CSV" / SEARCH_STRINGS_FILENAME,
        DATA_IN_DIR / LEGACY_CONFIG_FILENAME,
        DATA_IN_DIR / "CSV" / LEGACY_CONFIG_FILENAME,
    ])
    for path in candidates:
        if path.is_file():
            return path.resolve()

    scoped_candidates: list[tuple[int, Path]] = []
    for filename in (SEARCH_STRINGS_FILENAME, LEGACY_CONFIG_FILENAME):
        for path in DATA_IN_DIR.glob(f"SS*/CSV/{filename}"):
            scoped_name = path.parent.parent.name
            parsed_id = _extract_ss_id_from_scope_name(scoped_name)
            if parsed_id >= 0:
                scoped_candidates.append((parsed_id, path))

    if scoped_candidates:
        scoped_candidates.sort(key=lambda item: item[0])
        return scoped_candidates[-1][1].resolve()

    raise FileNotFoundError(
        "Search-strings CSV not found. Expected one of: "
        f"{DATA_IN_DIR / SEARCH_STRINGS_FILENAME}, "
        f"{DATA_IN_DIR / 'CSV' / SEARCH_STRINGS_FILENAME}, "
        f"{DATA_IN_DIR / LEGACY_CONFIG_FILENAME}, "
        f"{DATA_IN_DIR / 'CSV' / LEGACY_CONFIG_FILENAME}"
    )


def _load_rows(path: Path) -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []

    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        if reader.fieldnames is None:
            raise ValueError(f"Search-strings CSV has no header: {path}")

        lookup = {_normalize_header(name): name for name in reader.fieldnames}
        id_col = lookup.get("SSID")
        query_col = lookup.get("SEARCHSTRING")
        if id_col is None or query_col is None:
            raise ValueError(
                "Search-strings CSV must contain columns SS_ID and SEARCH_STRING "
                f"(found: {reader.fieldnames})"
            )

        for raw in reader:
            id_text = str(raw.get(id_col, "")).strip()
            query_text = str(raw.get(query_col, "")).strip()
            if not id_text:
                continue
            try:
                ss_id = int(id_text)
            except ValueError as exc:
                raise ValueError(f"Invalid SS_ID value in {path}: {id_text!r}") from exc
            rows.append((ss_id, query_text))

    if not rows:
        raise ValueError(f"No SS_ID rows found in search-strings CSV: {path}")
    return rows


def resolve_search_scope(ss_id: int | None, config_csv: Path | None = None) -> SearchScope:
    config_path = resolve_config_path(config_csv, ss_id)
    rows = _load_rows(config_path)

    if ss_id is None:
        chosen_id, chosen_query = rows[-1]
        return SearchScope(ss_id=chosen_id, search_string=chosen_query, config_path=config_path)

    for row_id, row_query in rows:
        if row_id == ss_id:
            return SearchScope(ss_id=row_id, search_string=row_query, config_path=config_path)

    available = ", ".join(str(row_id) for row_id, _ in rows)
    raise ValueError(f"SS_ID={ss_id} not found in {config_path}. Available IDs: {available}")


def get_scope_dataout_dir(ss_id: int) -> Path:
    return DATA_OUT_DIR / f"SS{ss_id}"


def get_scope_datain_dir(ss_id: int) -> Path:
    return DATA_IN_DIR / f"SS{ss_id}"


def resolve_scoped_input_dir(ss_id: int, *parts: str) -> Path:
    """Resolve an input directory inside datain/SS{ID} with legacy fallback.

    Priority:
    1) src/datain/SS{ID}/<parts>
    2) src/datain/<parts>
    """
    scoped_candidates = [
        get_scope_datain_dir(ss_id).joinpath(*parts),
        DATA_IN_DIR / f"SS{ss_id:02d}" / Path(*parts),
    ]
    for scoped in scoped_candidates:
        if scoped.is_dir():
            return scoped

    legacy = DATA_IN_DIR.joinpath(*parts)
    if legacy.is_dir():
        return legacy

    # Return scoped path by default so callers can present a clear message.
    return scoped_candidates[0]
