"""Generate synthetic outpatient appointments; not representative NHS records."""
from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path
import random

FIELDS = [
    "appointment_id", "site", "specialty", "age_band", "booking_channel",
    "assisted_booking_needed", "referral_date", "appointment_date", "status",
]
SITES = ("North Clinic", "Central Hospital", "East Health Centre", "Riverside Clinic")
SPECIALTIES = ("Dermatology", "Cardiology", "Ophthalmology", "Orthopaedics", "ENT")
AGE_BANDS = ("18-39", "40-59", "60-74", "75+")
CHANNELS = ("Digital", "Telephone", "In person")
STATUSES = ("Attended", "Did not attend", "Patient cancelled", "Hospital cancelled")


def generate_rows(count: int = 2400, seed: int = 42) -> list[dict[str, str]]:
    if count < 1:
        raise ValueError("count must be positive")
    rng = random.Random(seed)
    base = date(2025, 4, 1)
    rows: list[dict[str, str]] = []
    for i in range(count):
        age_band = rng.choices(AGE_BANDS, weights=(23, 30, 28, 19), k=1)[0]
        assisted = rng.random() < (0.50 if age_band == "75+" else 0.25 if age_band == "60-74" else 0.12)
        channel = rng.choices(CHANNELS, weights=(20, 64, 16) if assisted else (63, 30, 7), k=1)[0]
        site = rng.choice(SITES)
        specialty = rng.choice(SPECIALTIES)
        referral = base + timedelta(days=rng.randrange(290))
        wait_days = rng.randrange(7, 140) + (12 if assisted else 0)
        appointment = referral + timedelta(days=wait_days)
        # These deliberately invented correlations are NOT real NHS evidence.
        dna_probability = 0.125 if assisted and channel == "Digital" else 0.055 if channel == "Digital" else 0.075
        draw = rng.random()
        if draw < dna_probability:
            status = "Did not attend"
        elif draw < dna_probability + 0.09:
            status = "Patient cancelled"
        elif draw < dna_probability + 0.09 + 0.065:
            status = "Hospital cancelled"
        else:
            status = "Attended"
        rows.append({
            "appointment_id": f"SYN-A-{i+1:06d}", "site": site, "specialty": specialty,
            "age_band": age_band, "booking_channel": channel,
            "assisted_booking_needed": "Yes" if assisted else "No",
            "referral_date": referral.isoformat(), "appointment_date": appointment.isoformat(),
            "status": status,
        })
    return rows


def write_csv(rows: list[dict[str, str]], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
