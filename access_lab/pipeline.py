"""Schema validation, quarantine, audit and SQLite load."""
from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import sqlite3

from .generate import FIELDS, AGE_BANDS, CHANNELS, SITES, SPECIALTIES, STATUSES

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS appointment (
 appointment_id TEXT PRIMARY KEY,
 site TEXT NOT NULL,
 specialty TEXT NOT NULL,
 age_band TEXT NOT NULL,
 booking_channel TEXT NOT NULL,
 assisted_booking_needed TEXT NOT NULL,
 referral_date TEXT NOT NULL,
 appointment_date TEXT NOT NULL,
 wait_days INTEGER NOT NULL CHECK(wait_days>=0),
 status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ingestion_audit (
 source_sha256 TEXT NOT NULL,
 source_rows INTEGER NOT NULL,
 accepted_rows INTEGER NOT NULL,
 rejected_rows INTEGER NOT NULL,
 loaded_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
"""


def validate_row(row: dict[str, str]) -> tuple[dict[str, str | int] | None, str | None]:
    if any(not row.get(col) for col in FIELDS):
        return None, "missing_required_field"
    if not row["appointment_id"].startswith("SYN-A-"):
        return None, "invalid_synthetic_identifier"
    if row["site"] not in SITES or row["specialty"] not in SPECIALTIES:
        return None, "invalid_site_or_specialty"
    if row["age_band"] not in AGE_BANDS or row["booking_channel"] not in CHANNELS:
        return None, "invalid_age_band_or_channel"
    if row["assisted_booking_needed"] not in ("Yes", "No") or row["status"] not in STATUSES:
        return None, "invalid_status_or_assistance"
    try:
        referral = date.fromisoformat(row["referral_date"])
        appointment = date.fromisoformat(row["appointment_date"])
    except ValueError:
        return None, "invalid_date"
    wait = (appointment - referral).days
    if wait < 0:
        return None, "appointment_before_referral"
    return {**row, "wait_days": wait}, None


def ingest(csv_path: str | Path, database_path: str | Path, quarantine_path: str | Path) -> dict[str, int | str]:
    csv_path, database_path, quarantine_path = map(Path, (csv_path, database_path, quarantine_path))
    database_path.parent.mkdir(parents=True, exist_ok=True)
    quarantine_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None or set(reader.fieldnames) != set(FIELDS):
            raise ValueError("CSV column contract does not match expected schema")
        raw = list(reader)
    digest = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    valid: list[dict] = []
    invalid: list[dict] = []
    observed: set[str] = set()
    for row in raw:
        normalized, reason = validate_row(row)
        key = row.get("appointment_id", "")
        if not reason and key in observed:
            reason = "duplicate_appointment_id"
        if reason:
            invalid.append({"row": row, "reason": reason})
        else:
            assert normalized is not None
            valid.append(normalized)
            observed.add(key)
    with sqlite3.connect(database_path) as conn:
        conn.executescript(SCHEMA)
        # A complete, atomic refresh ensures repeatable reports from a supplied snapshot.
        with conn:
            conn.execute("DELETE FROM appointment")
            conn.executemany(
                "INSERT INTO appointment VALUES (:appointment_id,:site,:specialty,:age_band,"
                ":booking_channel,:assisted_booking_needed,:referral_date,:appointment_date,:wait_days,:status)",
                valid,
            )
            conn.execute(
                "INSERT INTO ingestion_audit(source_sha256,source_rows,accepted_rows,rejected_rows) VALUES(?,?,?,?)",
                (digest, len(raw), len(valid), len(invalid)),
            )
    quarantine_path.write_text(json.dumps(invalid, indent=2), encoding="utf-8")
    return {"source_rows": len(raw), "accepted_rows": len(valid), "rejected_rows": len(invalid), "sha256": digest}
