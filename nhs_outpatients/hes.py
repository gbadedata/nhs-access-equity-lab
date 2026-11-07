"""Load NHS England Hospital Outpatient Activity (HES) 2025-26 published files.

Two publisher conventions matter:

* ``*`` in MEASURE_VALUE is a suppressed small count, not zero and not missing
  at random. It is kept as ``None`` and reported; totals that include it are
  flagged as lower bounds.
* Appointment outcome totals are built from the 15 "Attendance Summary by Gender"
  measures (attended, DNA, patient cancelled, hospital cancelled, unknown, each
  by gender), which sum to the publication's 150.3 million appointments.
"""
from __future__ import annotations

from collections import defaultdict
import csv
from dataclasses import dataclass, field
from pathlib import Path

from .xlsx import read_sheet

OUTCOME_PREFIX = {"01": "attended", "02": "attended", "03": "attended",
                  "04": "dna", "05": "dna", "06": "dna",
                  "07": "patient_cancelled", "08": "patient_cancelled", "09": "patient_cancelled",
                  "10": "hospital_cancelled", "11": "hospital_cancelled", "12": "hospital_cancelled",
                  "13": "unknown", "14": "unknown", "15": "unknown"}
OUTCOMES = ("attended", "dna", "patient_cancelled", "hospital_cancelled", "unknown")


@dataclass
class Organisation:
    level: str
    code: str
    name: str
    measures: dict[tuple[str, str], int | None] = field(default_factory=dict)

    def value(self, measure_type: str, measure: str) -> int | None:
        return self.measures.get((measure_type, measure))

    @property
    def suppressed_cells(self) -> int:
        return sum(1 for v in self.measures.values() if v is None)

    def outcomes(self) -> dict[str, int]:
        totals = dict.fromkeys(OUTCOMES, 0)
        for (kind, measure), value in self.measures.items():
            if kind == "Attendance Summary by Gender" and value is not None:
                totals[OUTCOME_PREFIX[measure[:2]]] += value
        totals["appointments"] = sum(totals[k] for k in OUTCOMES)
        return totals

    def outcome_cells_suppressed(self) -> int:
        return sum(1 for (kind, _), v in self.measures.items() if kind == "Attendance Summary by Gender" and v is None)


def load_provider_level(path: Path) -> dict[tuple[str, str], Organisation]:
    """PLA CSV (long format) -> {(geography level, code): Organisation}."""
    organisations: dict[tuple[str, str], Organisation] = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        expected = {"REPORTING_PERIOD", "GEOGRAPHY_LEVEL", "ORGANISATION_CODE", "ORGANISATION_DESCRIPTION",
                    "MEASURE_TYPE", "MEASURE", "MEASURE_VALUE"}
        if set(reader.fieldnames or ()) != expected:
            raise ValueError(f"Unexpected PLA columns: {reader.fieldnames}")
        for row in reader:
            if row["REPORTING_PERIOD"] != "2526":
                raise ValueError(f"Unexpected reporting period {row['REPORTING_PERIOD']}")
            key = (row["GEOGRAPHY_LEVEL"], row["ORGANISATION_CODE"])
            org = organisations.setdefault(key, Organisation(*key, row["ORGANISATION_DESCRIPTION"]))
            raw = row["MEASURE_VALUE"].strip()
            if raw == "*":
                value = None
            else:
                number = float(raw)
                value = int(number) if number.is_integer() else number
            org.measures[(row["MEASURE_TYPE"], row["MEASURE"])] = value
    return organisations


def _table(path: Path, sheet: str, header_first_cell: str) -> list[list]:
    """Rows of a published summary table, from its header row to the first blank row."""
    rows = read_sheet(path, sheet)
    start = next(i for i, r in enumerate(rows) if r and isinstance(r[0], str) and r[0].strip() == header_first_cell)
    out = []
    for r in rows[start:]:
        if not r or r[0] in (None, ""):
            break
        out.append(r)
    return out


def report_tables(path: Path) -> dict[str, list[dict]]:
    """The six summary tables of the HES report workbook, as lists of dicts."""
    def as_dicts(table):
        header = [str(h).strip() if h is not None else "" for h in table[0]]
        return [{h: v for h, v in zip(header, row) if h} for row in table[1:]]

    tables = {
        "trend": as_dicts(_table(path, "Summary Report 1", "Year")),
        "region": as_dicts(_table(path, "Summary Report 2", "Commissioning Region")),
        "age_sex": as_dicts(_table(path, "Summary Report 3", "Age (yrs)")),
        "ethnicity": as_dicts(_table(path, "Summary Report 4", "Ethnicity (grouped)")),
        "imd": as_dicts(_table(path, "Summary Report 5", "English Indices of Deprivation")),
    }
    specialty = _table(path, "Summary Report 6", "Treatment Specialty code & description")
    tables["specialty"] = [
        {"code": r[0], "name": r[1], "attendances": r[2], "dnas": r[3]} for r in specialty[1:] if isinstance(r[0], int)
    ]
    return tables


def ethnicity_recording(path: Path) -> dict:
    """How many attendances have no usable ethnicity (Not known / Not stated)."""
    counts = defaultdict(int)
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["MEASURE_TYPE"] == "Activity by Ethnicity" and row["MEASURE"].startswith("All Attendances - "):
                counts[row["MEASURE"].split(" - ", 1)[1]] = int(row["MEASURE_VALUE"])
    total = counts.pop("All Ethnic Groups")
    missing = counts.get("Not Known", 0) + counts.get("Not stated", 0)
    return {"attendances": total, "not_known": counts.get("Not Known", 0), "not_stated": counts.get("Not stated", 0),
            "missing": missing, "missing_share": missing / total}
