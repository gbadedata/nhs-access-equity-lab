"""Build every figure in the report from the official files, with denominators named."""
from __future__ import annotations

import csv
import math
from pathlib import Path

from . import eric, gpad, hes, sources
from .stats import (funnel_limits, overdispersion, overdispersion_untransformed, ratio_limits,
                    ratio_overdispersion, risk_ratio, wilson)

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


AGE_ATTENDED = "Attended Appointments by Age Group"
AGE_DNA = "Did not Attend by Age Group"
Z95, Z998 = 1.96, 3.09
MIN_PEER_GROUP = 8  # fewer trusts than this and a peer group gets no limits of its own


def _age_counts(org) -> dict[str, tuple[int, int, int]]:
    """{age band: (attended, DNAs, suppressed cells)} from the provider file's age tables."""
    bands = {m for (kind, m) in org.measures if kind in (AGE_ATTENDED, AGE_DNA)}
    out = {}
    for band in sorted(bands, key=str.strip):  # sorted: a set's order changes between runs
        a, d = org.measures.get((AGE_ATTENDED, band)), org.measures.get((AGE_DNA, band))
        out[band.strip()] = (a or 0, d or 0, (a is None and (AGE_ATTENDED, band) in org.measures)
                             + (d is None and (AGE_DNA, band) in org.measures))
    return out


def _flag(value: float, lower: float, upper: float) -> str | None:
    return "above" if value > upper else "below" if value < lower else None


def providers(orgs, trusts_path: Path, trust_types: dict[str, dict] | None = None) -> dict:
    """Compare NHS trusts' DNA rates three ways: against England, allowing for age, and against similar trusts.

    The rate is DNAs / (attended + DNAs), the standard definition for comparing
    missed appointments. Cancellations are left out of the denominator because
    trusts record them very differently: some report none at all. Trusts whose
    unknown-outcome share exceeds 5% are screened out and listed instead.
    """
    trusts = _ods_trusts(trusts_path)
    nat_org = orgs[("01.National", "ENG")]
    national = nat_org.outcomes()
    p0 = national["dna"] / (national["attended"] + national["dna"])
    p0_old = national["dna"] / (national["appointments"] - national["unknown"])
    band_rate = {b: d / (a + d) for b, (a, d, _) in _age_counts(nat_org).items()}
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
        n = o["attended"] + o["dna"]
        record = {"code": code, "name": org.name, "appointments": o["appointments"], "attended": o["attended"],
                  "dna": o["dna"], "attended_or_dna": n,
                  "cancellations": o["patient_cancelled"] + o["hospital_cancelled"],
                  "unknown_share": o["unknown"] / o["appointments"],
                  "dna_rate": o["dna"] / n if n else None,
                  "dna_share_of_recorded_outcomes": o["dna"] / known if known else None,
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
            continue
        ages = _age_counts(org)
        observed = sum(d for _, d, _ in ages.values())
        expected = sum((a + d) * band_rate[b] for b, (a, d, _) in ages.items())
        record["age"] = {"observed": observed, "expected": expected, "ratio": observed / expected,
                         "suppressed_cells": sum(s for _, _, s in ages.values()),
                         "volume_in_bands": sum(a + d for a, d, _ in ages.values())}
        linked.append(record)

    # View 1: against England.
    events, volumes = [r["dna"] for r in linked], [r["attended_or_dna"] for r in linked]
    disp = overdispersion(events, volumes, p0)
    tau2_raw = overdispersion_untransformed(events, volumes, p0)
    old_disp = overdispersion(events, [r["appointments"] - round(r["unknown_share"] * r["appointments"]) for r in linked], p0_old)
    for r in linked:
        n, rate = r["attended_or_dna"], r["dna_rate"]
        r["flag"] = _flag(rate, *funnel_limits(n, p0, Z998, disp["tau2"]))
        r["naive_flag"] = _flag(rate, *funnel_limits(n, p0, Z998)) is not None
        half = Z998 * math.sqrt(p0 * (1 - p0) / n + tau2_raw)
        r["flag_untransformed"] = _flag(rate, p0 - half, p0 + half)
        known = r["appointments"] - round(r["unknown_share"] * r["appointments"])
        r["flag_old_denominator"] = _flag(r["dna_share_of_recorded_outcomes"], *funnel_limits(known, p0_old, Z998, old_disp["tau2"]))

    # View 2: allowing for age (indirect standardisation against England's age-specific rates).
    age_disp = ratio_overdispersion([r["age"]["observed"] for r in linked], [r["age"]["expected"] for r in linked])
    for r in linked:
        r["age"]["flag"] = _flag(r["age"]["ratio"], *ratio_limits(r["age"]["expected"], Z998, age_disp["tau2"]))

    # View 3: against trusts of the same type, allowing for age.
    peer = None
    if trust_types is not None:
        peer = _peer_groups(linked, trust_types)

    linked.sort(key=lambda r: -r["dna_rate"])
    views = ["flag", "age"] + (["peer"] if peer else [])
    def flagged(r, view):
        return r["flag"] if view == "flag" else r[view]["flag"]
    stand_out = [r for r in linked if any(flagged(r, v) for v in views)]
    return {
        "measure": "DNAs / (attended + DNAs)",
        "p0": p0, "min_appointments": MIN_PROVIDER_APPOINTMENTS, "max_unknown_share": MAX_UNKNOWN_OUTCOME_SHARE,
        "overdispersion": disp, "age_overdispersion": age_disp, "age_bands": band_rate,
        "peer_groups": peer, "min_peer_group": MIN_PEER_GROUP, "nhs_trusts": linked, "screened_out_unknown_outcomes": screened,
        "other_providers": sorted(other, key=lambda r: -r["appointments"]),
        "providers_below_volume_threshold": small, "codes_matched_after_removing_X_suffix": sorted(suffix_stripped),
        "above_998": sum(1 for r in linked if r["flag"] == "above"),
        "below_998": sum(1 for r in linked if r["flag"] == "below"),
        "naive_outside_998": sum(1 for r in linked if r["naive_flag"]),
        "age_above_998": sum(1 for r in linked if r["age"]["flag"] == "above"),
        "age_below_998": sum(1 for r in linked if r["age"]["flag"] == "below"),
        "age_band_rounding": {
            "max_volume_gap": max(abs(r["age"]["volume_in_bands"] - r["attended_or_dna"]) / r["attended_or_dna"] for r in linked),
            "dna_gap_over_1pct": [(r["name"], r["dna"] - r["age"]["observed"], r["dna"]) for r in linked
                                  if r["dna"] and abs(r["dna"] - r["age"]["observed"]) / r["dna"] > 0.01],
        },
        "trusts_reporting_no_cancellations": sorted(r["name"] for r in linked if r["cancellations"] == 0),
        "stand_out_in_every_view": [r["name"] for r in stand_out if all(flagged(r, v) for v in views)
                                    and len({flagged(r, v) for v in views}) == 1],
        "stand_out_in_any_view": [r["name"] for r in stand_out],
        "sensitivity_untransformed": {
            "tau2": tau2_raw,
            "outside_998": sum(1 for r in linked if r["flag_untransformed"]),
            "flagged_only_untransformed": [r["name"] for r in linked if r["flag_untransformed"] and not r["flag"]],
        },
        "sensitivity_old_denominator": {
            "measure": "DNAs / appointments with a recorded outcome (v0.2.2)",
            "p0": p0_old,
            "above_998": sum(1 for r in linked if r["flag_old_denominator"] == "above"),
            "below_998": sum(1 for r in linked if r["flag_old_denominator"] == "below"),
            "flagged": [r["name"] for r in linked if r["flag_old_denominator"]],
        },
        "dna_rate_range": [linked[-1]["dna_rate"], linked[0]["dna_rate"]],
    }


def _peer_groups(linked: list[dict], trust_types: dict[str, dict]) -> dict:
    """Compare each trust's age-adjusted ratio with trusts of the same ERIC type."""
    groups: dict[str, list[dict]] = {}
    for r in linked:
        info = trust_types.get(r["ods_code"])
        group = info["peer_group"] if info else "Not in ERIC"
        r["peer"] = {"group": group, "eric_type": info["type"] if info else None, "flag": None}
        groups.setdefault(group, []).append(r)
    summary = {}
    for group, members in sorted(groups.items()):
        observed = sum(r["age"]["observed"] for r in members)
        expected = sum(r["age"]["expected"] for r in members)
        level = observed / expected
        entry = {"trusts": len(members), "trusts_in_eric": sum(1 for v in trust_types.values() if v["peer_group"] == group),
                 "group_ratio_to_england": level, "limits": len(members) >= MIN_PEER_GROUP}
        if entry["limits"] and group != "Not in ERIC":
            exp = [r["age"]["expected"] * level for r in members]
            disp = ratio_overdispersion([r["age"]["observed"] for r in members], exp)
            entry["overdispersion"] = disp
            for r, e in zip(members, exp):
                ratio = r["age"]["observed"] / e
                r["peer"].update(ratio=ratio, flag=_flag(ratio, *ratio_limits(e, Z998, disp["tau2"])))
        else:
            for r in members:
                r["peer"]["ratio"] = None
        entry["above_998"] = sum(1 for r in members if r["peer"]["flag"] == "above")
        entry["below_998"] = sum(1 for r in members if r["peer"]["flag"] == "below")
        summary[group] = entry
    return summary


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
        "providers": providers(orgs, sources.path_of("ods_nhs_trusts"),
                               eric.load_trust_types(sources.path_of("eric_trust_types"))),
        "general_practice": general_practice(sources.path_of("gpad_national_overview")),
        "sources": sources.manifest(),
    }
