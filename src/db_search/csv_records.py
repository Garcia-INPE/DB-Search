from __future__ import annotations

import csv
import re
from pathlib import Path


UNKNOWN_YEAR_VALUES = {"", "????", "none", "nan"}


def sanitize_field(value: object) -> str:
    text = "" if value is None else str(value)
    return text.replace(";", ",").strip()


def normalize_title_key(title: str) -> str:
    text = sanitize_field(title).casefold()
    return re.sub(r"\s+", " ", text).strip()


def normalize_record(db_name: object, year: object, title: object) -> tuple[str, str, str]:
    db_text = sanitize_field(db_name)
    year_text = sanitize_field(year) or "????"
    title_text = sanitize_field(title)
    return db_text, year_text, title_text


def read_records(csv_path: Path) -> list[tuple[str, str, str]]:
    if not csv_path.is_file():
        return []

    records: list[tuple[str, str, str]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter=";")
        for row in reader:
            if not row:
                continue
            while len(row) < 3:
                row.append("")

            db_name, year, title = normalize_record(row[0], row[1], row[2])
            if (db_name.upper(), year.upper(), title.upper()) == ("DB", "YEAR", "TITLE"):
                continue
            if not db_name and not title:
                continue
            records.append((db_name, year, title))
    return records


def has_known_year(year: str) -> bool:
    return sanitize_field(year).casefold() not in UNKNOWN_YEAR_VALUES


def choose_record(current: tuple[str, str, str], candidate: tuple[str, str, str]) -> tuple[str, str, str]:
    current_db, current_year, current_title = current
    _, candidate_year, candidate_title = candidate

    chosen_year = current_year
    if not has_known_year(current_year) and has_known_year(candidate_year):
        chosen_year = candidate_year

    chosen_title = current_title
    if len(candidate_title) > len(current_title):
        chosen_title = candidate_title

    return current_db, chosen_year, chosen_title


def merge_records(
    existing: list[tuple[str, str, str]],
    incoming: list[tuple[str, str, str]],
) -> tuple[list[tuple[str, str, str]], int]:
    merged: list[tuple[str, str, str]] = []
    index_by_key: dict[tuple[str, str], int] = {}

    for record in [*existing, *incoming]:
        db_name, year, title = normalize_record(*record)
        if not db_name or not title:
            continue

        key = (db_name.casefold(), normalize_title_key(title))
        if key not in index_by_key:
            index_by_key[key] = len(merged)
            merged.append((db_name, year, title))
            continue

        position = index_by_key[key]
        merged[position] = choose_record(merged[position], (db_name, year, title))

    added_count = max(0, len(merged) - len(existing))
    return merged, added_count


def write_records(csv_path: Path, records: list[tuple[str, str, str]]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        for db_name, year, title in records:
            handle.write(f"{db_name};{year};{title}\n")


def merge_records_into_csv(
    csv_path: Path,
    incoming: list[tuple[str, str, str]],
) -> tuple[int, int]:
    existing = read_records(csv_path)
    merged, added_count = merge_records(existing, incoming)
    write_records(csv_path, merged)
    return len(merged), added_count