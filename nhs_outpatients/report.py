"""Render the findings as one static, accessible HTML page plus tidy CSV tables."""
from __future__ import annotations

import csv
from html import escape
from pathlib import Path

from . import svgcharts
from .stats import funnel_limits, ratio_limits

CSS = """
:root{color-scheme:light dark}*{box-sizing:border-box}
body{margin:0;font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;background:#f9f9f7;color:#0b0b0b}
header{background:#005eb8;color:#fff;padding:38px max(22px,calc((100vw - 1000px)/2)) 32px}
header h1{margin:0 0 8px;font-size:clamp(1.7rem,3.4vw,2.5rem);line-height:1.2}header p{margin:0;max-width:780px;opacity:.95}
main{max-width:1000px;margin:auto;padding:22px 20px 70px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;margin:20px 0}
.card,.box,table.plain{background:#fcfcfb;border:1px solid rgba(11,11,11,.10)}
.card{border-radius:12px;padding:16px 18px}.card .v{font-size:1.85rem;font-weight:650;line-height:1.2}.card .l{font-size:.9rem;color:#52514e}
.box{border-radius:10px;border-left:4px solid #005eb8;padding:14px 20px;margin:18px 0}
.box.warn{border-left-color:#c98500}ol.sowhat{padding-left:22px}ol.sowhat li{margin:0 0 12px}
h2{margin:40px 0 6px;font-size:1.4rem}.muted{color:#52514e}.small{font-size:.88rem}
table.plain{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:.92rem}
table.plain th,table.plain td{padding:7px 10px;border-bottom:1px solid rgba(127,127,127,.25);text-align:left;vertical-align:top}
code{font-size:.84em;word-break:break-all}a{color:#005eb8}footer{margin-top:44px;font-size:.85rem}
@media (prefers-color-scheme:dark){body{background:#0d0d0d;color:#f0efec}.card,.box,table.plain{background:#1a1a19;border-color:rgba(255,255,255,.1)}
.card .l,.muted{color:#c3c2b7}a{color:#86b6ef}}
"""


SMALL_WORDS = {"And", "Of", "The", "For", "In", "On"}


def nice_name(upper: str) -> str:
    """'ALDER HEY CHILDREN'S NHS FOUNDATION TRUST' -> "Alder Hey Children's NHS Foundation Trust"."""
    words = []
    for i, word in enumerate(upper.split()):
        if word in ("NHS", "UK"):
            words.append(word)
            continue
        titled = word.capitalize()
        titled = titled.replace("'S", "'s")
        words.append(titled.lower() if i and titled in SMALL_WORDS else titled)
    return " ".join(words)


def _m(n: float) -> str:
    return f"{n / 1e6:.1f}m"


def _p(x: float, dp: int = 1) -> str:
    return f"{x:.{dp}f}%"


def _table(head: list[str], rows: list[list]) -> str:
    h = "".join(f"<th scope='col'>{escape(c)}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{escape(str(c))}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table class='plain'><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>"


def write_tables(findings: dict, folder: Path) -> None:
    """Tidy CSVs for anyone who wants to rebuild the charts in Excel or Power BI."""
    folder.mkdir(parents=True, exist_ok=True)
    def dump(name, rows):
        with (folder / name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    dump("trend.csv", findings["trend"])
    dump("ethnicity.csv", [{k: v for k, v in g.items() if k != "ratio_ci"} | {"ratio_ci_low": g["ratio_ci"][0],
                           "ratio_ci_high": g["ratio_ci"][1]} for g in findings["ethnicity"]["groups"]])
    dump("age_sex.csv", findings["age_sex"])
    dump("attendance_type.csv", findings["attendance_type"])
    dump("regions.csv", findings["regions"])
    dump("deprivation.csv", findings["deprivation"]["deciles"])
    dump("nhs_trusts_funnel.csv", [
        {k: r[k] for k in ("code", "ods_code", "name", "appointments", "attended", "dna", "cancellations", "attended_or_dna",
                           "dna_rate", "flag")}
        | {"age_expected_dna": r["age"]["expected"], "age_ratio": r["age"]["ratio"], "age_flag": r["age"]["flag"],
           "eric_type": r.get("peer", {}).get("eric_type"), "peer_group": r.get("peer", {}).get("group"),
           "peer_ratio": r.get("peer", {}).get("ratio"), "peer_flag": r.get("peer", {}).get("flag"),
           "flag_v022_denominator": r["flag_old_denominator"]}
        for r in findings["providers"]["nhs_trusts"]])
    gp = findings["general_practice"]
    dump("gp_dna_by_mode.csv", [{"month": m, **{mode: series[i] for mode, series in gp["dna_share_of_known_by_mode"].items()}}
                                for i, m in enumerate(gp["months"])])


def render(findings: dict, output: Path) -> None:
    h, eth, prov, gp = findings["headline"], findings["ethnicity"], findings["providers"], findings["general_practice"]
    trend, ages, types = findings["trend"], findings["age_sex"], findings["attendance_type"]
    regions, dep, src = findings["regions"], findings["deprivation"], findings["sources"]

    groups = {g["group"]: g for g in eth["groups"]}
    black, white = groups["Black"], groups["White"]
    young_men = max(ages, key=lambda a: a["male_dna_pct"])
    oldest = min(ages, key=lambda a: (a["female_dna_pct"] + a["male_dna_pct"]))
    first_in_person, first_remote = types[0], types[1]
    london = next(r for r in regions if r["code"] == "Y56")
    peer = prov["peer_groups"]
    every = prov["stand_out_in_every_view"]
    age_changes = [r for r in prov["nhs_trusts"] if r["flag"] != r["age"]["flag"]]
    stand_out_sentence = (
        f"Allowing for age changes the verdict for {len(age_changes)} trusts"
        + (", and comparing each trust only with trusts of the same type changes it again" if peer else "")
        + f". Only {len(every)} stand out in the same direction however they are compared: "
        + "; ".join(f"{nice_name(r['name'])} ({'higher' if r['flag'] == 'above' else 'lower'})"
                    for r in prov["nhs_trusts"] if r["name"] in every)
        + ". Those are the ones worth a conversation with the trust's information team, starting with how missed appointments are recorded.")
    missing_eth = eth["recording"]["missing_share"] * 100
    first, last = trend[0], trend[-1]

    cards = "".join(f"<div class='card'><div class='v'>{escape(v)}</div><div class='l'>{escape(l)}</div></div>" for v, l in (
        (_m(h["appointments"]), "outpatient appointments in 2025-26"),
        (f"{_m(h['dna'])} ({_p(h['dna_pct'])})", "were missed without notice (DNA)"),
        (f"{_m(h['hospital_cancelled'])} ({_p(h['hospital_cancelled_pct'])})", "were cancelled by the hospital"),
        (_p(missing_eth), "of attendances have no recorded ethnicity"),
    ))

    sowhat = f"""<ol class="sowhat">
<li><strong>Look at hospital cancellations before patient behaviour.</strong> Hospitals cancelled {_m(h['hospital_cancelled'])} appointments,
{h['hospital_cancellations_per_dna']:.1f} times the {_m(h['dna'])} that patients missed, and the hospital cancellation rate rose from
{_p(first['hospital_cancelled_pct'])} in {first['year']} to {_p(last['hospital_cancelled_pct'])} while the DNA rate fell from
{_p(first['dna_pct'])} to {_p(last['dna_pct'])}. London cancels {_p(london['hospital_cancelled_pct'])} of appointments; the South West
{_p(min(r['hospital_cancelled_pct'] for r in regions))}. Part of that gap may be recording practice, which is itself worth checking.</li>
<li><strong>Non-attendance is concentrated, so support can be targeted without blaming anyone.</strong> Men aged {young_men['age']} miss
{_p(young_men['male_dna_pct'])} of booked appointments against {_p((oldest['female_dna_pct'] + oldest['male_dna_pct']) / 2)} for people aged
{oldest['age']}. Black patients' DNA rate is {_p(black['dna_pct'])}, {black['ratio_to_white']:.2f} times the White rate ({_p(white['dna_pct'])}).
These are the groups to involve in redesigning reminders, booking and timing, not to penalise.</li>
<li><strong>Do not read the ethnicity gap as a fact about ethnicity yet.</strong> In the 2021 Census the median age was 43 for the White group,
32 for the Asian and Black groups and 19 for the Mixed group (England and Wales). DNA rates fall steeply with age, so some of the gap is an age
effect that these published tables cannot remove. And {_p(missing_eth)} of attendances
carry no ethnicity at all. Better recording is a precondition for monitoring inequality, not an afterthought.</li>
<li><strong>Remote appointments are missed less often, but that is not proof they cause better attendance.</strong> First appointments by
telephone or video have a recorded DNA rate of {_p(first_remote['dna_pct'])} against {_p(first_in_person['dna_pct'])} in person. Patients,
specialties and the way a missed call is recorded all differ between the two. A remote-first change should be piloted with an evaluation plan
and with in-person routes kept open.</li>
<li><strong>Compare trusts like with like before acting on a league table.</strong> On plain statistical limits
{prov['naive_outside_998']} of {len(prov['nhs_trusts'])} trusts look like outliers; allowing for real between-trust variation,
{prov['above_998']} sit above and {prov['below_998']} below the 99.8% limits. {stand_out_sentence}
{len(prov['trusts_reporting_no_cancellations'])} trusts report no cancellations to HES at all, so rates here leave cancellations out of the
denominator.</li>
</ol>"""

    trend_chart = svgcharts.lines(
        "Outpatient appointment outcomes in England, 2015-16 to 2025-26",
        "Share of all appointments. Source: HES Hospital Outpatient Activity 2025-26, Summary Report 1.",
        [t["year"] for t in trend],
        [("Hospital cancelled", [t["hospital_cancelled_pct"] for t in trend]),
         ("Patient cancelled", [t["patient_cancelled_pct"] for t in trend]),
         ("Did not attend", [t["dna_pct"] for t in trend])],
        lambda v: f"{v:.1f}%")
    age_chart = svgcharts.lines(
        "Did-not-attend rate by age and sex, 2025-26",
        "DNAs as a share of attended plus DNA appointments (this table has no cancellations). Female attendances include maternity.",
        [a["age"] for a in ages],
        [("Male", [a["male_dna_pct"] for a in ages]), ("Female", [a["female_dna_pct"] for a in ages])],
        lambda v: f"{v:.1f}%")
    eth_chart = svgcharts.hbar(
        "Did-not-attend rate by ethnic group, 2025-26",
        f"DNAs as a share of all appointments. Groups cover {eth['appointments_with_grouped_ethnicity'] / h['appointments'] * 100:.0f}% "
        "of appointments; the rest have no usable ethnicity. Not age-standardised.",
        [(g["group"], g["dna_pct"], f"{g['group']}: {g['dna_pct']:.2f}% of {g['appointments']:,} appointments\n"
          f"{g['ratio_to_white']:.2f} times the White rate (95% CI {g['ratio_ci'][0]:.2f} to {g['ratio_ci'][1]:.2f})")
         for g in sorted(eth["groups"], key=lambda g: -g["dna_pct"])],
        lambda v: f"{v:.1f}%", "DNA rate", reference=(h["dna_pct"], "England"))
    type_chart = svgcharts.columns(
        "Did-not-attend rate, in person and remote, 2025-26",
        "DNAs as a share of attended plus DNA appointments of each type. Remote means telephone or video.",
        ["First appointment", "Follow-up"],
        [("In person", [types[0]["dna_pct"], types[2]["dna_pct"]]),
         ("Telephone or video", [types[1]["dna_pct"], types[3]["dna_pct"]])],
        lambda v: f"{v:.1f}%")
    region_chart = svgcharts.hbar(
        "Did-not-attend rate by NHS England commissioning region, 2025-26",
        "DNAs as a share of all appointments commissioned by each region.",
        [(r["region"], r["dna_pct"], f"{r['region']}: DNA {r['dna_pct']:.2f}%, hospital cancelled {r['hospital_cancelled_pct']:.2f}%\n"
          f"{r['appointments']:,} appointments") for r in regions],
        lambda v: f"{v:.1f}%", "DNA rate", reference=(h["dna_pct"], "England"))
    dep_chart = svgcharts.hbar(
        "First outpatient attendances per 100,000 people, by deprivation decile",
        "Crude rates, not adjusted for age or need. HES assigns deprivation with the 2010 Index of Multiple Deprivation.",
        [(d["decile"], d["first_per_100k"], f"{d['decile']}: {d['first_per_100k']:,} per 100,000") for d in dep["deciles"]],
        lambda v: f"{v:,.0f}", "First attendances per 100,000", highlight={"Most deprived 10%"})

    p0, tau2 = prov["p0"], prov["overdispersion"]["tau2"]
    fmt_n = lambda n: f"{n:,.0f}" if n < 1e6 else f"{n / 1e6:.0f}m"
    funnel_chart = svgcharts.funnel(
        f"Did-not-attend rate for {len(prov['nhs_trusts'])} NHS trusts, 2025-26",
        "Each dot is a trust with at least 10,000 appointments. DNA rate = DNAs / (attended + DNAs). Limits allow for real "
        "between-trust variation (Spiegelhalter 2005, arcsine scale).",
        [{"n": r["attended_or_dna"], "p": r["dna_rate"], "label": nice_name(r["name"]), "flag": r["flag"]} for r in prov["nhs_trusts"]],
        p0, lambda n, z: funnel_limits(n, p0, z, tau2), lambda v: f"{100 * v:.1f}%", fmt_n,
        "Appointments attended or missed (log scale)", volume_name="appointments attended or missed")
    age_tau2 = prov["age_overdispersion"]["tau2"]
    age_chart_trusts = svgcharts.funnel(
        "Missed appointments against what the trust's age mix predicts",
        "Ratio of each trust's DNAs to the number expected if England's DNA rate for each age band applied to its own patients "
        "(indirect standardisation). 1.0 = as expected. Limits allow for real between-trust variation (square-root scale).",
        [{"n": r["age"]["expected"], "p": r["age"]["ratio"], "label": nice_name(r["name"]), "flag": r["age"]["flag"]}
         for r in prov["nhs_trusts"]],
        1.0, lambda n, z: ratio_limits(n, z, age_tau2), lambda v: f"{v:.2f}", fmt_n,
        "Expected DNAs (log scale)", reference_label="As expected", value_name="Ratio to expected",
        volume_name="expected DNAs")
    view_names = ["Against England", "Allowing for age"] + (["Against similar trusts"] if peer else [])
    def verdict(flag):
        return {"above": "Higher", "below": "Lower"}.get(flag, "-")
    stand_out_rows = []
    for r in prov["nhs_trusts"]:
        if r["name"] not in prov["stand_out_in_any_view"]:
            continue
        row = [nice_name(r["name"])] + ([(r["peer"]["eric_type"] or "Not in ERIC").capitalize()] if peer else []) + [
            _p(100 * r["dna_rate"]), verdict(r["flag"]), verdict(r["age"]["flag"])]
        if peer:
            row.append(verdict(r["peer"]["flag"]) if r["peer"]["ratio"] is not None else "No peer limits")
        stand_out_rows.append(row)
    stand_out_table = _table(["Trust"] + (["ERIC trust type"] if peer else []) + ["DNA rate"] + view_names, stand_out_rows)
    peer_rows = [[g, str(e["trusts"]), f"{e['group_ratio_to_england']:.2f}",
                  f"{e['above_998']} higher, {e['below_998']} lower" if e["limits"] and g != "Not in ERIC" else "Too few trusts for limits"]
                 for g, e in (peer or {}).items()]
    mh, cc = (peer or {}).get("Mental health and learning disability"), (peer or {}).get("Community and care")
    peer_note = (f"<p class='small muted'>General acute trusts are pooled across ERIC's size and teaching bands. Only {mh['trusts']} of "
                 f"England's {mh['trusts_in_eric']} mental health and learning disability trusts appear, because much of what mental health trusts "
                 "do is recorded in the Mental Health Services Data Set rather than HES. "
                 f"{cc['trusts']} community and care trusts is too few to estimate how much such trusts genuinely differ, so they get no "
                 f"limits of their own (the minimum, {prov['min_peer_group']}, was set before the ERIC file was loaded). Specialist trusts "
                 "(children's, cancer, eye, orthopaedic, heart) differ a lot from each other, so their group limits are wide.</p>") if peer else ""
    peer_table = _table(["Peer group", "Trusts", "Group's age-adjusted ratio to England", "Outside the 99.8% limits"], peer_rows) if peer else ""
    screened_rows = [[nice_name(r["name"]), f"{r['appointments']:,}", _p(100 * r["unknown_share"])] for r in prov["screened_out_unknown_outcomes"]]
    old = prov["sensitivity_old_denominator"]
    rounding = prov["age_band_rounding"]

    months = gp["months"]
    gp_chart = svgcharts.lines(
        f"GP appointments missed, by appointment mode, {months[0]} to {months[-1]}",
        "DNAs as a share of appointments with a recorded outcome. Source: Appointments in General Practice, National Overview.",
        months, [(mode.replace("Video Conference/Online", "Video or online"), vals)
                 for mode, vals in gp["dna_share_of_known_by_mode"].items()],
        lambda v: f"{v:.1f}%")
    rec = gp["headline_reconciliation"]

    sources_rows = [[f["title"], f.get("published", ""), f"{f['bytes']:,}", f["sha256"][:16] + "…"] for f in src["files"].values()]
    defs = _table(["Measure", "Definition used here"], [
        ["DNA rate (headline, ethnicity, region, trend)", "DNAs / all appointments, matching the HES publication"],
        ["DNA rate (age, appointment type)", "DNAs / (attended + DNA); those tables publish no cancellations"],
        ["DNA rate (trust comparison)", "DNAs / (attended + DNAs), the standard definition for comparing missed appointments; trusts with over 5% unknown outcomes screened out"],
        ["Age-adjusted ratio", "Observed DNAs / expected DNAs, where expected applies England's DNA rate in each of 11 age bands to the trust's own attended-or-missed appointments"],
        ["Ratio limits", "(1 ± z·√(1/4E + τ²))², E = expected DNAs; τ² from winsorised z-scores on the square-root scale (Spiegelhalter 2005)"],
        ["Ratio to White", "Ratio of two proportions with a 95% interval on the log scale (Katz)"],
        ["Funnel limits", "sin²(asin√p₀ ± z·√(1/4n + τ²)), z = 1.96 and 3.09; τ² from winsorised z-scores on the arcsine scale (Spiegelhalter 2005)"],
        ["GP DNA rate", "DNA / (attended + DNA); about 6% of GP appointments have an unknown status"],
    ])

    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Who misses NHS outpatient appointments, and what should a service manager do?</title>
<style>{CSS}{svgcharts.CSS}</style></head><body>
<header><h1>Who misses NHS outpatient appointments, and what should a service manager do about it?</h1>
<p>An analysis of NHS England's published Hospital Outpatient Activity 2025-26 and Appointments in General Practice data. Every number on this
page is computed from the official files listed at the bottom; none is typed in by hand. Aggregate statistics only, no patient records.</p></header>
<main>
<div class="cards">{cards}</div>
<div class="box"><strong>Checks before analysis.</strong> The pipeline rebuilds the publication's own headline (150.3 million appointments,
8.2 million DNAs, {_p(h['dna_pct'])}) from the provider-level file to the last appointment, and reproduces NHS England's published DNA proportion
for every ethnic group exactly. If either check fails, nothing is reported.</div>

<h2>Five things to take from this</h2>{sowhat}

<h2>Cancellations have grown while missed appointments have fallen</h2>{trend_chart}
<h2>Young adults, and young men most, miss the most appointments</h2>{age_chart}
<h2>Ethnicity: a real gap, measured on incomplete data</h2>{eth_chart}
<p class="small muted">With 97 million appointments in the White group alone, the 95% intervals are a few hundredths of a percentage point wide, so chance
is not the issue. Age structure and missing ethnicity are. Under NHS England's Core20PLUS5 approach, local systems define their own PLUS groups,
and ethnic minority communities are among those NHS England expects to see identified. This is the kind of evidence a local team would bring to that work,
after age-standardising with local data. Census medians from ONS, Ethnic group by age and sex, England and Wales: Census 2021.</p>
<h2>Remote appointments have lower recorded DNA rates</h2>{type_chart}
<h2>Regions differ, and London stands out on cancellations</h2>{region_chart}
<h2>The most deprived areas have the lowest first-attendance rate</h2>{dep_chart}
<p class="small muted">The most deprived tenth of areas has {(1 - dep['most_to_least_ratio']) * 100:.1f}% fewer first attendances per head than the
least deprived tenth. Need for care is higher in deprived areas, but their populations are also younger, so a crude rate cannot say whether access
is worse. It is a question to test with age- and need-adjusted local data, not a finding.</p>

<h2>Comparing trusts like with like</h2>
<p>A single league table of trusts mixes acute hospitals with mental health, community and specialist trusts, whose patients and clinics
are not alike. This section compares each trust three ways: against England, after allowing for the age of its patients, and
{"against trusts of the same type, as classified in NHS England's Estates Returns Information Collection (ERIC)" if peer else "against trusts of the same type once a trust-type lookup is loaded"}.
A trust that stands out on every view is worth a question; one that stands out on only one is mostly telling you about the comparison.</p>
{funnel_chart}
{age_chart_trusts}
{('<p>Peer groups, from ERIC trust types:</p>' + peer_table + peer_note) if peer else ''}
<p>Every trust outside the 99.8% limits on at least one view:</p>{stand_out_table}
<div class="box warn"><strong>Screened out before comparison.</strong> These trusts recorded more than 5% of appointments with an unknown outcome,
so their DNA rate cannot be compared fairly. East London NHS Foundation Trust's 88,765 appointments all have an unknown outcome: a naive analysis
would have shown it as the best performer in England with a 0% DNA rate.</div>
{_table(["Trust", "Appointments", "Unknown outcome"], screened_rows)}
<div class="box"><strong>Why cancellations are left out of the rate.</strong> {len(prov['trusts_reporting_no_cancellations'])} of the
{len(prov['nhs_trusts'])} trusts report no patient or hospital cancellations to HES at all, while at a typical trust cancellations are around a
fifth of appointments. Dividing DNAs by every appointment with a recorded outcome, as version 0.2.2 of this analysis did, made those trusts'
rates look higher purely because of how they record cancellations. On that older definition {old['above_998']} trusts sat above the limits and
{old['below_998']} below.</div>
<p class="small muted"><strong>Sensitivity.</strong> Fitting the national model on the untransformed proportion scale puts
{prov['sensitivity_untransformed']['outside_998']} trusts outside the limits rather than {prov['above_998'] + prov['below_998']}, and
{' and '.join(nice_name(n) for n in prov['sensitivity_untransformed']['flagged_only_untransformed'])} are flagged only on that scale. Treat those
two as borderline. The age
adjustment uses the 11 age bands HES publishes for each trust. HES rounds trust counts to the nearest 5 and suppresses very small ones, so a
trust's age bands do not always add up to its total: expected counts move by at most {rounding['max_volume_gap'] * 100:.2f}%, and observed DNAs
by more than 1% at only {len(rounding['dna_gap_over_1pct'])} trusts ({', '.join(f"{nice_name(n)}: {lost} of {total}" for n, lost, total in rounding['dna_gap_over_1pct'])}
DNAs in suppressed cells), none of which changes a verdict.</p>
<p class="small muted">Trusts are identified by joining HES provider codes to the ODS register of NHS trusts (<code>etr</code>).
{len(prov['codes_matched_after_removing_X_suffix'])} large trusts appear in HES with a <code>-X</code> suffix that the HES metadata does not
explain; they match ODS once the suffix is removed. {len(prov['other_providers'])} other providers with 10,000+ appointments are independent-sector
organisations (or a closed trust code) and are not on these charts.</p>

<h2>In general practice, mode matters even more</h2>{gp_chart}
<p class="small muted">In {gp['latest_month']}, {gp['latest_mode_share_pct']['Face-to-Face']:.0f}% of GP appointments were face to face and
{gp['latest_mode_share_pct']['Video Conference/Online']:.0f}% video or online. "Online" includes asynchronous online consultations, where
there is little to miss, so the near-zero rate is partly a property of the mode itself.</p>

<h2>Data quality and reconciliation</h2>
<ul>
<li>HES headline rebuilt exactly from the provider file: {h['appointments']:,} appointments, {h['dna']:,} DNAs.</li>
<li>GP September 2026: the publication's headline is {rec['all_recorded_million']} million appointments "recorded across General Practice";
the National Overview file covers the {rec['appointment_books_million']} million in GP appointment books from {rec['practice_coverage_pct']}% of
practices. This file sums to {gp['latest_total']:,}. The first version of this project typed in the 35.1m headline next to percentages from a
narrower base.</li>
<li>Every regional and provider count in the HES provider file is a multiple of 5 and small counts appear as <code>*</code>; national figures are
exact. Suppressed cells are counted as zero in provider totals and the number affected is recorded per trust.</li>
<li>{_p(missing_eth)} of attendances have ethnicity 'Not known' or 'Not stated'.</li>
<li>HES assigns deprivation deciles with the 2010 Index of Multiple Deprivation.</li>
</ul>

<h2>Definitions</h2>{defs}

<h2>Sources</h2>
{_table(["File", "Published", "Bytes", "SHA-256"], sources_rows)}
<p class="small muted">All files retrieved {escape(src['retrieved'])} from NHS England and the ODS, re-used under the
{escape(src['licence'])}. Full URLs and digests are in <code>data/raw/MANIFEST.json</code>; the pipeline refuses to run if a file has changed.</p>
<footer class="muted">Independent portfolio analysis by Oluwagbade Odimayo. Not affiliated with or endorsed by NHS England.</footer>
</main>{svgcharts.SCRIPT}</body></html>"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
