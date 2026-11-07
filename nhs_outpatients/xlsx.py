"""Read cell values from an .xlsx workbook with the standard library only.

Enough for NHS England's published tables (shared strings, inline strings,
numbers, booleans). Formulas are read as their cached values, which is what
the publisher saved. Formatting, merged cells and dates-as-serials are not
interpreted; the HES tables used here do not need them.
"""
from __future__ import annotations

import re
import zipfile
from xml.etree import ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
CELL_REF = re.compile(r"([A-Z]+)(\d+)")


def _column_index(letters: str) -> int:
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - 64)
    return index - 1


def _number(text: str) -> int | float:
    value = float(text)
    return int(value) if value.is_integer() and "e" not in text.lower() and "." not in text else value


def sheet_names(path) -> list[str]:
    with zipfile.ZipFile(path) as book:
        root = ET.fromstring(book.read("xl/workbook.xml"))
        return [s.get("name") for s in root.find("m:sheets", NS)]


def read_sheet(path, name: str) -> list[list]:
    """Return the sheet as a list of rows; empty cells are None."""
    with zipfile.ZipFile(path) as book:
        workbook = ET.fromstring(book.read("xl/workbook.xml"))
        rels = ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))
        targets = {r.get("Id"): r.get("Target") for r in rels.findall("rel:Relationship", NS)}
        rel_id = next((s.get(f"{{{NS['r']}}}id") for s in workbook.find("m:sheets", NS) if s.get("name") == name), None)
        if rel_id is None:
            raise KeyError(f"No sheet named {name!r}")
        target = targets[rel_id].lstrip("/")
        target = target if target.startswith("xl/") else f"xl/{target}"
        shared: list[str] = []
        if "xl/sharedStrings.xml" in book.namelist():
            for item in ET.fromstring(book.read("xl/sharedStrings.xml")).findall("m:si", NS):
                shared.append("".join(t.text or "" for t in item.iter(f"{{{NS['m']}}}t")))
        sheet = ET.fromstring(book.read(target))

    rows: dict[int, dict[int, object]] = {}
    for cell in sheet.iter(f"{{{NS['m']}}}c"):
        match = CELL_REF.fullmatch(cell.get("r", ""))
        if not match:
            continue
        col, row = _column_index(match.group(1)), int(match.group(2)) - 1
        kind = cell.get("t")
        raw = cell.find("m:v", NS)
        if kind == "inlineStr":
            value = "".join(t.text or "" for t in cell.iter(f"{{{NS['m']}}}t"))
        elif raw is None or raw.text is None:
            continue
        elif kind == "s":
            value = shared[int(raw.text)]
        elif kind in ("str", "e"):
            value = raw.text
        elif kind == "b":
            value = raw.text == "1"
        else:
            value = _number(raw.text)
        rows.setdefault(row, {})[col] = value
    if not rows:
        return []
    width = max(max(cols) for cols in rows.values()) + 1
    return [[rows.get(r, {}).get(c) for c in range(width)] for r in range(max(rows) + 1)]
