"""Trust types from NHS England's Estates Returns Information Collection (ERIC), trust-level file.

ERIC is the standard published source for an NHS trust's type (acute by size,
teaching, specialist or multi-service; mental health and learning disability;
community; ambulance). It is used here only to group trusts with similar ones,
never as a measure in its own right.
"""
from __future__ import annotations

import csv
from pathlib import Path

CODE_COLUMNS = ("trust code", "organisation code", "org code")
TYPE_COLUMNS = ("trust type", "organisation type")

# ERIC type -> peer group used for like-for-like comparison. General acute trusts are
# pooled across size bands; specialist trusts are kept apart because they are not
# general hospitals; care trusts sit with community trusts.
PEER_GROUPS = {
    "ACUTE - SMALL": "Acute",
    "ACUTE - MEDIUM": "Acute",
    "ACUTE - LARGE": "Acute",
    "ACUTE - TEACHING": "Acute",
    "ACUTE - MULTI-SERVICE": "Acute",
    "ACUTE - SPECIALIST": "Acute specialist",
    "MENTAL HEALTH AND LEARNING DISABILITY": "Mental health and learning disability",
    "MENTAL HEALTH (INCLUDING LEARNING DISABILITY)": "Mental health and learning disability",
    "COMMUNITY": "Community and care",
    "CARE TRUST": "Community and care",
    "CARE": "Community and care",
    "AMBULANCE": "Ambulance",
}


def _column(header: list[str], candidates: tuple[str, ...]) -> int:
    lowered = [h.strip().lower() for h in header]
    for name in candidates:
        if name in lowered:
            return lowered.index(name)
    raise ValueError(f"ERIC file has none of the columns {candidates}: {header}")


def load_trust_types(path: Path) -> dict[str, dict]:
    """{ODS trust code: {"type": ERIC type, "peer_group": group}}. Unknown types are refused, not guessed."""
    # NHS England publishes the ERIC CSV in Windows-1252 (the pound sign in its headers is byte 0xA3).
    with Path(path).open(encoding="cp1252", newline="") as handle:
        rows = list(csv.reader(handle))
    header_at = next((i for i, row in enumerate(rows[:20]) if any(c.strip().lower() in TYPE_COLUMNS for c in row)), None)
    if header_at is None:
        raise ValueError("No trust type column found in the first 20 rows of the ERIC file")
    header = rows[header_at]
    code_i, type_i = _column(header, CODE_COLUMNS), _column(header, TYPE_COLUMNS)
    types: dict[str, dict] = {}
    for row in rows[header_at + 1:]:
        if len(row) <= max(code_i, type_i) or not row[code_i].strip():
            continue
        code, kind = row[code_i].strip().upper(), " ".join(row[type_i].split()).upper()
        if kind not in PEER_GROUPS:
            raise ValueError(f"Unrecognised ERIC trust type {kind!r} for {code}")
        if code in types and types[code]["type"] != kind:
            raise ValueError(f"Trust {code} has two ERIC types: {types[code]['type']} and {kind}")
        types[code] = {"type": kind, "peer_group": PEER_GROUPS[kind]}
    if len(types) < 150:
        raise ValueError(f"Only {len(types)} trusts read from the ERIC file; expected about 200")
    return types
