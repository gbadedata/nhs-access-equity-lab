"""Build every figure in the report from the official files, with denominators named."""
from __future__ import annotations

import csv
from pathlib import Path

from . import gpad, hes, sources
from .stats import funnel_halfwidth, overdispersion, risk_ratio, wilson

PUBLISHED_HEADLINE = {  # as stated in the text of the HES 2025-26 publication page
    "appointments_million": 150.3, "attendances_million": 116.9, "dnas_million": 8.2, "dna_share_pct": 5.4,
    "dna_share_pct_2019_20": 6.2,
}
GPAD_HEADLINE_SEPT_2026 = {  # publication page text, September 2026
    "all_recorded_million": 35.1, "appointment_books_million": 34.1, "practice_coverage_pct": 98.9,
}
MIN_PROVIDER_APPOINTMENTS = 10_000
MAX_UNKNOWN_OUTCOME_SHARE = 0.05  # data-quality screen for the provider comparison
REGIONS = ("Y56", "Y58", "Y59", "Y60", "Y61", "Y62", "Y63")


def _pct(part: float, whole: float) -> float:
    return 100 * part / whole


def headline(orgs) -> dict:
    eng = orgs[("01.National", "ENG")].outcomes()
    n = eng["appointments"]
    return {
        **eng,
        "dna_pct": _pct(eng["dna"], n), "attended_pct": _pct(eng["attended"], n),
        "patient_cancelled_pct": _pct(eng["patient_cancelled"], n),
        "hospital_cancelled_pct": _pct(eng["hospital_cancelled"], n),
        "hospital_cancellations_per_dna": eng["hospital_cancelled"] / eng["dna"],
        "matches_published_headline": (
            round(n / 1e6, 1) == PUBLISHED_HEADLINE["appointments_million"]
            and round(eng["attended"] / 1e6, 1) == PUBLISHED_HEADLINE["attendances_million"]
            and round(eng["dna"] / 1e6, 1) == PUBLISHED_HEADLINE["dnas_million"]
            and round(_pct(eng["dna"], n), 1) == PUBLISHED_HEADLINE["dna_share_pct"]),
    }


def trend(tables) -> list[dict]:
    return [{"year": r["Year"], "appointments": r["Total"], "dna_pct": r["Did not attends (DNAs) %"],
             "hospital_cancelled_pct": r["Hospital cancellations %"],
             "patient_cancelled_pct": r["Patient cancellations %"]} for r in tables["trend"]]


def ethnicity(tables, recording) -> dict:
    rows = {r["Ethnicity (grouped)"]: r for r in tables["ethnicity"]}
    white = rows["White"]
    groups = []
    for name, r in rows.items():
        appts, dnas = r["All Appointments"], r["Did not attend"]
        lo, hi = wilson(dnas, appts)
        rr = risk_ratio(dnas, appts, white["Did not attend"], white["All Appointments"]) if name != "White" else (1.0, 1.0, 1.0)
        groups.append({"group": name, "appointments": appts, "dnas": dnas, "dna_pct": _pct(dnas, appts),
                       "ci_low_pct": 100 * lo, "ci_high_pct": 100 * hi,
                       "ratio_to_white": rr[0], "ratio_ci": [rr[1], rr[2]],
                       "published_proportion_pct": 100 * r["Proportion of DNAs from all appointments"]})
    covered = sum(g["appointments"] for g in groups)
    return {"groups": groups, "appointments_with_grouped_ethnicity": covered, "recording": recording}


def age_sex(tables) -> list[dict]:
    out = []
    for r in tables["age_sex"]:
        female_att = r["Attended - Female Maternity"] + r["Attended - Female Non-Maternity"]
        male_att = r["Attended - Male"]
        f_dna, m_dna = r["Did Not Attend - All Female"], r["Did Not Attend - Male"]
        out.append({"age": r["Age (yrs)"],
                    "female_dna_pct": _pct(f_dna, female_att + f_dna), "male_dna_pct": _pct(m_dna, male_att + m_dna),
                    "female_attended": female_att, "female_dna": f_dna, "male_attended": male_att, "male_dna": m_dna})
    return out


def attendance_type(orgs) -> list[dict]:
    eng = orgs[("01.National", "ENG")]
    kind = "Attendance Type"
    pairs = (("First, in person", "01.Attended first appointment", "06.Did not attend first appointment"),
             ("First, telephone or video", "02.Attended first tele consultation", "07.Did not attend first tele consultation"),
             ("Follow-up, in person", "03.Attended subsequent appointment", "08.Did not attend subsequent appointment"),
             ("Follow-up, telephone or video", "04.Attended subsequent tele consultation",
              "09.Did not attend subsequent tele consultation"))
    out = []
    for label, att_m, dna_m in pairs:
        att, dna = eng.value(kind, att_m), eng.value(kind, dna_m)
        out.append({"type": label, "attended": att, "dna": dna, "dna_pct": _pct(dna, att + dna)})
    return out


def regions(orgs) -> list[dict]:
    out = []
    for code in REGIONS:
        org = orgs[("02.Commissioning Region", code)]
        o = org.outcomes()
        name = org.name.title().replace(" Commissioning Region", "").replace(" And ", " and ").replace(" Of ", " of ")
        out.append({"code": code, "region": name,
                    "appointments": o["appointments"], "dna_pct": _pct(o["dna"], o["appointments"]),
                    "hospital_cancelled_pct": _pct(o["hospital_cancelled"], o["appointments"]),
                    "suppressed_outcome_cells": org.outcome_cells_suppressed()})
    return sorted(out, key=lambda r: -r["dna_pct"])


def deprivation(tables) -> dict:
    rows = [{"decile": r["English Indices of Deprivation"], "first_per_100k": r["First Attendances per 100,000 population"],
             "population": r["National population per IMD decile"]}
            for r in tables["imd"] if r["English Indices of Deprivation"] != "Total Activity"]
    most, least = rows[0], rows[-1]
    return {"deciles": rows, "most_to_least_ratio": most["first_per_100k"] / least["first_per_100k"],
            "imd_version": "2010 (as stated in the HES metadata)"}


def specialties(tables) -> list[dict]:
    return [{"specialty": r["name"].replace(" Service", ""), "attendances": r["attendances"], "dnas": r["dnas"],
             "dna_pct": _pct(r["dnas"], r["attendances"] + r["dnas"])} for r in tables["specialty"]]


def _ods_trusts(path: Path) -> dict[str, dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {r[0]: {"name": r[1], "closed": r[11] or None} for r in csv.reader(handle) if len(r) == 27}


def providers(orgs, trusts_path: Path) -> dict:
    """Compare NHS trusts' DNA rates on a funnel plot.

    Rate = DNAs / appointments with a recorded outcome, so that trusts which send
    'unknown outcome' records are neither rewarded nor penalised. Trusts whose
    unknown-outcome share exceeds 5% are screened out and listed instead.
    """
    trusts = _ods_trusts(trusts_path)
    national = orgs[("01.National", "ENG")].outcomes()
    p0 = national["dna"] / (national["appointments"] - national["unknown"])
    linked, other, screened, small = [], [], [], 0
    suffix_stripped = []
    for (level, code), org in orgs.items():
        if level != "03.Provider":
            continue
        o = org.outcomes()
        if o["appointments"] < MIN_PROVIDER_APPOINTMENTS:
            small += 1
            continue
        ods_code = code[:-2] if code.endswith("-X") else code
        known = o["appointments"] - o["unknown"]
        record = {"code": code, "name": org.name, "appointments": o["appointments"], "known_outcome": known,
                  "dna": o["dna"], "unknown_share": o["unknown"] / o["appointments"],
                  "dna_rate": o["dna"] / known if known else None,
                  "suppressed_outcome_cells": org.outcome_cells_suppressed()}
        trust = trusts.get(ods_code)
        if not trust or trust["closed"]:
            record["ods_status"] = "closed NHS trust code" if trust else "not an NHS trust in ODS etr"
            other.append(record)
            continue
        record["ods_code"] = ods_code
        if ods_code != code:
            suffix_stripped.append(code)
        if record["unknown_share"] > MAX_UNKNOWN_OUTCOME_SHARE:
            screened.append(record)
        else:
            linked.append(record)

    disp = overdispersion([r["dna"] for r in linked], [r["known_outcome"] for r in linked], p0)
    for r in linked:
        n = r["known_outcome"]
        adjusted = funnel_halfwidth(n, p0, 3.09, disp["tau2"])
        naive = funnel_halfwidth(n, p0, 3.09)
        r["flag"] = "above" if r["dna_rate"] > p0 + adjusted else "below" if r["dna_rate"] < p0 - adjusted else None
        r["naive_flag"] = abs(r["dna_rate"] - p0) > naive
    linked.sort(key=lambda r: -r["dna_rate"])
    return {
        "p0": p0, "min_appointments": MIN_PROVIDER_APPOINTMENTS, "max_unknown_share": MAX_UNKNOWN_OUTCOME_SHARE,
        "overdispersion": disp, "nhs_trusts": linked, "screened_out_unknown_outcomes": screened,
        "other_providers": sorted(other, key=lambda r: -r["appointments"]),
        "providers_below_volume_threshold": small, "codes_matched_after_removing_X_suffix": sorted(suffix_stripped),
        "above_998": sum(1 for r in linked if r["flag"] == "above"),
        "below_998": sum(1 for r in linked if r["flag"] == "below"),
        "naive_outside_998": sum(1 for r in linked if r["naive_flag"]),
        "dna_rate_range": [linked[-1]["dna_rate"], linked[0]["dna_rate"]],
    }


def general_practice(path: Path) -> dict:
    months = gpad.load(path)
    series = {mode: [100 * (gpad.dna_share_of_known(m["mode"].get(mode, {})) or 0) for m in months.values()]
              for mode in gpad.MODES[:3]}
    latest_key = list(months)[-1]
    latest = months[latest_key]
    unknown_share = 100 * latest["status"]["Unknown"] / latest["total"]
    return {
        "months": list(months), "dna_share_of_known_by_mode": series, "latest_month": latest_key,
        "latest_total": latest["total"],
        "latest_dna_share_of_known": 100 * gpad.dna_share_of_known(latest["status"]),
        "latest_unknown_status_pct": unknown_share,
        "latest_mode_share_pct": {mode: 100 * sum(latest["mode"].get(mode, {}).values()) / latest["total"]
                                  for mode in gpad.MODES},
        "headline_reconciliation": {**GPAD_HEADLINE_SEPT_2026,
                                    "national_overview_csv_million": round(latest["total"] / 1e6, 2)},
    }


def build() -> dict:
    sources.verify()
    orgs = hes.load_provider_level(sources.path_of("hes_provider_level"))
    tables = hes.report_tables(sources.path_of("hes_report_tables"))
    recording = hes.ethnicity_recording(sources.path_of("hes_ethnicity_imd"))
    return {
        "headline": headline(orgs),
        "trend": trend(tables),
        "ethnicity": ethnicity(tables, recording),
        "age_sex": age_sex(tables),
        "attendance_type": attendance_type(orgs),
        "regions": regions(orgs),
        "deprivation": deprivation(tables),
        "specialties": specialties(tables),
        "providers": providers(orgs, sources.path_of("ods_nhs_trusts")),
        "general_practice": general_practice(sources.path_of("gpad_national_overview")),
        "sources": sources.manifest(),
    }
