"""Appointments in General Practice (GPAD) National Overview CSV."""
from __future__ import annotations

from collections import defaultdict
import csv
from datetime import datetime
from pathlib import Path

COLUMNS = ["APPOINTMENT_MONTH", "APPT_STATUS", "HCP_TYPE", "APPT_MODE", "SERVICE_SETTING",
           "CONTEXT_TYPE", "NATIONAL_CATEGORY", "APPOINTMENTS"]
MODES = ("Face-to-Face", "Telephone", "Video Conference/Online", "Home Visit")


def load(path: Path) -> dict[str, dict]:
    """month (YYYY-MM) -> totals by status and by (mode, status)."""
    months: dict[str, dict] = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != COLUMNS:
            raise ValueError(f"Unexpected GPAD columns: {reader.fieldnames}")
        for row in reader:
            month = datetime.strptime(row["APPOINTMENT_MONTH"], "%b%Y").strftime("%Y-%m")
            entry = months.setdefault(month, {"total": 0, "status": defaultdict(int),
                                              "mode": defaultdict(lambda: defaultdict(int))})
            n = int(row["APPOINTMENTS"])
            entry["total"] += n
            entry["status"][row["APPT_STATUS"]] += n
            entry["mode"][row["APPT_MODE"]][row["APPT_STATUS"]] += n
    return dict(sorted(months.items()))


def dna_share_of_known(counts: dict) -> float | None:
    """DNAs as a share of appointments whose outcome was recorded (attended + DNA).

    Around 6% of GPAD appointments have status 'Unknown'; including them in the
    denominator would understate DNAs by an amount that varies by mode.
    """
    known = counts.get("Attended", 0) + counts.get("DNA", 0)
    return counts.get("DNA", 0) / known if known else None
