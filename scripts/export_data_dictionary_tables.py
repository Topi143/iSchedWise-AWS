#!/usr/bin/env python3
"""Export ASCII tables from DATA_DICTIONARY.txt into CSV and optional XLSX.

This script parses box-drawn ASCII tables that use `+---+` borders and `| ... |`
rows, then writes each table to its own CSV file for easy import into
Google Sheets/Docs.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import List, Optional


SPECIAL_LABEL_PATTERNS = [
    (re.compile(r"^\s*TABLE INDEX\s*$", re.IGNORECASE), "table_index"),
    (
        re.compile(r"^\s*9\.1\s+Foreign Key Reference Table\s*$", re.IGNORECASE),
        "foreign_key_reference_table",
    ),
    (
        re.compile(r"^\s*9\.2\s+Table Cardinality Summary\s*$", re.IGNORECASE),
        "table_cardinality_summary",
    ),
    (re.compile(r"^\s*KEY CONVENTIONS\s*$", re.IGNORECASE), "key_conventions"),
]


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = value.strip("_")
    return value or "table"


def is_border_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("+"):
        return False
    return bool(re.fullmatch(r"[+=\-\s]+", stripped))


def split_ascii_row(line: str) -> List[str]:
    # Expects a row that starts and ends with '|'.
    body = line.strip()
    body = body[1:-1]
    return [cell.strip() for cell in body.split("|")]


def is_continuation_row(cells: List[str]) -> bool:
    if not cells:
        return False
    first = cells[0].strip()
    has_content_elsewhere = any(cell.strip() for cell in cells[1:])
    return not first and has_content_elsewhere


def merge_wrapped_rows(rows: List[List[str]]) -> tuple[List[str], List[List[str]]]:
    if not rows:
        return [], []

    headers = rows[0]
    width = len(headers)
    merged: List[List[str]] = []

    for raw in rows[1:]:
        cells = raw[:]
        if len(cells) < width:
            cells.extend([""] * (width - len(cells)))
        elif len(cells) > width:
            cells = cells[: width - 1] + [" ".join(cells[width - 1 :])]

        if not any(cell.strip() for cell in cells):
            continue

        if is_continuation_row(cells) and merged:
            previous = merged[-1]
            for idx, value in enumerate(cells):
                value = value.strip()
                if not value:
                    continue
                if previous[idx]:
                    previous[idx] = f"{previous[idx]} {value}".strip()
                else:
                    previous[idx] = value
            continue

        merged.append(cells)

    return headers, merged


def unique_sheet_name(base: str, used: set[str]) -> str:
    clean = re.sub(r"[\\/*?:\[\]]", "_", base)
    clean = clean[:31] if clean else "Sheet"
    if clean not in used:
        used.add(clean)
        return clean

    suffix = 2
    while True:
        trial = f"{clean[:28]}_{suffix}" if len(clean) > 28 else f"{clean}_{suffix}"
        if trial not in used:
            used.add(trial)
            return trial
        suffix += 1


def detect_table_name(
    pending_label: Optional[str],
    pending_table_name: Optional[str],
    fallback_index: int,
    seen_names: defaultdict[str, int],
) -> tuple[str, Optional[str], Optional[str]]:
    base = pending_label or pending_table_name or f"table_{fallback_index:02d}"
    count = seen_names[base]
    seen_names[base] += 1
    final_name = base if count == 0 else f"{base}_{count + 1}"

    if pending_label:
        pending_label = None
    if pending_table_name:
        pending_table_name = None

    return final_name, pending_label, pending_table_name


def parse_ascii_tables(input_path: Path) -> List[dict]:
    lines = input_path.read_text(encoding="utf-8").splitlines()

    tables: List[dict] = []
    seen_names: defaultdict[str, int] = defaultdict(int)

    pending_label: Optional[str] = None
    pending_table_name: Optional[str] = None

    in_table = False
    raw_rows: List[List[str]] = []

    def flush_table() -> None:
        nonlocal raw_rows, pending_label, pending_table_name
        if not raw_rows:
            return

        headers, rows = merge_wrapped_rows(raw_rows)
        if not headers:
            raw_rows = []
            return

        table_name, pending_label, pending_table_name = detect_table_name(
            pending_label=pending_label,
            pending_table_name=pending_table_name,
            fallback_index=len(tables) + 1,
            seen_names=seen_names,
        )
        tables.append(
            {
                "name": table_name,
                "headers": headers,
                "rows": rows,
            }
        )
        raw_rows = []

    for line in lines:
        stripped = line.strip()

        # Track explicit named table sections.
        match = re.match(r"^\s*Table:\s*(.+?)\s*$", line)
        if match:
            pending_table_name = slugify(match.group(1))

        # Track special headings that precede non-"Table:" tables.
        for pattern, label in SPECIAL_LABEL_PATTERNS:
            if pattern.match(stripped):
                pending_label = label
                break

        if in_table:
            if line.lstrip().startswith("|"):
                raw_rows.append(split_ascii_row(line))
                continue
            if is_border_line(line):
                continue

            in_table = False
            flush_table()

        if is_border_line(line):
            in_table = True
            raw_rows = []

    if in_table:
        flush_table()

    return tables


def write_csv_tables(tables: List[dict], out_dir: Path) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    created: List[Path] = []

    for index, table in enumerate(tables, start=1):
        filename = f"{index:02d}_{table['name']}.csv"
        path = out_dir / filename
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(table["headers"])
            writer.writerows(table["rows"])
        created.append(path)

    return created


def write_xlsx_tables(tables: List[dict], xlsx_path: Path) -> bool:
    try:
        from openpyxl import Workbook
    except Exception:
        return False

    workbook = Workbook()
    default_sheet = workbook.active
    workbook.remove(default_sheet)

    used_sheet_names: set[str] = set()
    for table in tables:
        sheet_name = unique_sheet_name(table["name"], used_sheet_names)
        sheet = workbook.create_sheet(title=sheet_name)

        sheet.append(table["headers"])
        for row in table["rows"]:
            sheet.append(row)

    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(xlsx_path)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export ASCII tables from DATA_DICTIONARY.txt to CSV/XLSX."
    )
    parser.add_argument(
        "--input",
        default="docs/DATA_DICTIONARY.txt",
        help="Path to the source ASCII data dictionary text file.",
    )
    parser.add_argument(
        "--outdir",
        default="docs/data_dictionary_exports",
        help="Directory where CSV files will be generated.",
    )
    parser.add_argument(
        "--xlsx",
        default="docs/data_dictionary_exports/data_dictionary_tables.xlsx",
        help="Optional XLSX output path (requires openpyxl).",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.outdir)
    xlsx_path = Path(args.xlsx)

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        return 1

    tables = parse_ascii_tables(input_path)
    if not tables:
        print("ERROR: No ASCII tables detected.")
        return 1

    created = write_csv_tables(tables, out_dir)
    xlsx_ok = write_xlsx_tables(tables, xlsx_path)

    print(f"EXPORTED_TABLES|{len(created)}")
    print(f"CSV_OUTPUT_DIR|{out_dir}")
    print(f"FIRST_CSV|{created[0]}")
    print(f"LAST_CSV|{created[-1]}")
    if xlsx_ok:
        print(f"XLSX_OUTPUT|{xlsx_path}")
    else:
        print("XLSX_OUTPUT|skipped (openpyxl unavailable)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
