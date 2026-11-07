"""Descriptive outpatient access measures. No causal or clinical claims."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import statistics

DIMENSIONS = ("site", "specialty", "age_band", "booking_channel", "assisted_booking_needed")


def percentile(values: list[int], fraction: float) -> float | None:
    if not values:
        return None
    items = sorted(values)
    rank = (len(items) - 1) * fraction
    low = int(rank)
    high = min(low + 1, len(items) - 1)
    return round(items[low] + (items[high] - items[low]) * (rank - low), 1)


def aggregate(rows: list[dict], min_group_size: int = 10) -> dict:
    if min_group_size < 1:
        raise ValueError("min_group_size must be positive")
    n = len(rows)
    if n < min_group_size:
        return {"suppressed": True, "record_count": None, "reason": "small_group"}
    status_counts = {status: sum(row["status"] == status for row in rows)
                     for status in ("Attended", "Did not attend", "Patient cancelled", "Hospital cancelled")}
    waits = [int(row["wait_days"]) for row in rows]
    return {
        "suppressed": False,
        "record_count": n,
        "attended": status_counts["Attended"],
        "did_not_attend": status_counts["Did not attend"],
        "patient_cancelled": status_counts["Patient cancelled"],
        "hospital_cancelled": status_counts["Hospital cancelled"],
        "dna_percent_all_appointments": round(100 * status_counts["Did not attend"] / n, 2),
        "median_referral_to_appointment_days": round(statistics.median(waits), 1),
        "p90_referral_to_appointment_days": percentile(waits, .90),
    }


def build_metrics(database_path: str | Path, min_group_size: int = 10) -> dict:
    with sqlite3.connect(database_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = [dict(row) for row in conn.execute("SELECT * FROM appointment")]
    breakdowns: dict[str, dict] = {}
    for dimension in DIMENSIONS:
        groups = sorted({row[dimension] for row in rows})
        breakdowns[dimension] = {
            group: aggregate([row for row in rows if row[dimension] == group], min_group_size)
            for group in groups
        }
    return {
        "metadata": {
            "dataset": "fully synthetic, invented distributions",
            "definition": "DNA rate uses all appointments as denominator; no patient-level risk scoring",
            "waiting_measure": "referral to appointment days, NOT official RTT performance",
            "minimum_display_cell": min_group_size,
        },
        "overall": aggregate(rows, min_group_size), "by": breakdowns,
    }


def write_metrics(metrics: dict, file_path: str | Path) -> None:
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
