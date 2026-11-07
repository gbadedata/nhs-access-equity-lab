"""Accessible, dependency-free static HTML management dashboard."""
from __future__ import annotations

from html import escape
from pathlib import Path

CSS = """
:root{color-scheme:light;--blue:#005eb8;--navy:#102a43;--muted:#52677c;--light:#eff6fc;--edge:#dce5ee}
*{box-sizing:border-box}body{margin:0;background:#f5f7fb;font:16px/1.6 system-ui,-apple-system,Segoe UI,sans-serif;color:var(--navy)}
header{background:linear-gradient(125deg,#004b93,#0072ce);color:white;padding:44px max(24px,calc((100vw - 1060px)/2))}
header p{max-width:750px;opacity:.93}h1{font-size:clamp(2rem,4vw,3.2rem);margin:.1em 0}.eyebrow{text-transform:uppercase;letter-spacing:.16em;font-size:.75rem;font-weight:800}
main{max-width:1060px;padding:28px 22px 75px;margin:auto}.alert{border-left:5px solid #ed9b34;background:#fff7e7;padding:14px 20px;margin:0 0 25px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px}.card{background:white;border:1px solid var(--edge);border-radius:12px;padding:22px;box-shadow:0 4px 14px #102a4309}.card .value{font-size:2.1rem;font-weight:750;color:var(--blue)}.card .label{color:var(--muted);font-size:.9rem}
section{margin:36px 0}h2{font-size:1.55rem}h3{margin:22px 0 7px}table{width:100%;border-collapse:collapse;background:white;border:1px solid var(--edge)}th,td{padding:12px 14px;text-align:left;border-bottom:1px solid var(--edge)}th{background:#e8f2fc}tr:hover{background:#f3f9ff}
.visual{display:flex;align-items:center;gap:12px}.bar{width:120px;background:#e1eaf4;height:11px;border-radius:12px;overflow:hidden;flex-shrink:0}.bar>span{display:block;background:var(--blue);height:100%}
@media(max-width:650px){table{font-size:.82rem}th,td{padding:9px 6px}.bar{width:45px}}a{color:var(--blue)}footer{font-size:.86rem;color:var(--muted);border-top:1px solid var(--edge);padding-top:18px}
"""


def render(metrics: dict, output: str | Path) -> None:
    overall = metrics["overall"]
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    def card(value: object, label: str) -> str:
        return f'<div class="card"><div class="value">{escape(str(value))}</div><div class="label">{escape(label)}</div></div>'
    if overall["suppressed"]:
        cards = card("Suppressed", "Fewer than the minimum group size")
    else:
        cards = "".join((
            card(f'{overall["record_count"]:,}', "Synthetic appointments"),
            card(f'{overall["dna_percent_all_appointments"]:.2f}%', "Did-not-attend share"),
            card(overall["median_referral_to_appointment_days"], "Median referral-to-appointment days"),
            card(overall["p90_referral_to_appointment_days"], "90th-percentile days"),
        ))
    sections = []
    titles = {"site": "Across locations", "specialty": "Across specialties", "age_band": "By age band",
              "booking_channel": "By booking channel", "assisted_booking_needed": "By assisted-booking need"}
    for dim, title in titles.items():
        lines = []
        for label, stats in metrics["by"][dim].items():
            if stats["suppressed"]:
                lines.append(f"<tr><th scope='row'>{escape(label)}</th><td colspan='4'>Suppressed: fewer than {metrics['metadata']['minimum_display_cell']} records</td></tr>")
                continue
            percent = float(stats["dna_percent_all_appointments"])
            lines.append(
                f"<tr><th scope='row'>{escape(label)}</th><td>{stats['record_count']:,}</td>"
                f"<td><div class='visual'><div class='bar' aria-hidden='true'><span style='width:{min(100,percent):.1f}%'></span></div>{percent:.2f}%</div></td>"
                f"<td>{stats['median_referral_to_appointment_days']}</td><td>{stats['p90_referral_to_appointment_days']}</td></tr>"
            )
        sections.append(f"<section><h2>{escape(title)}</h2><table><thead><tr><th scope='col'>Group</th><th scope='col'>Appointments</th><th scope='col'>DNA (%)</th><th scope='col'>Median wait (days)</th><th scope='col'>P90 wait (days)</th></tr></thead><tbody>{''.join(lines)}</tbody></table></section>")
    html = f"""<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Access & Equity Lab | Synthetic outpatient operations</title><style>{CSS}</style></head>
<body><header><div class='eyebrow'>Healthcare data engineering · demonstration</div><h1>Access &amp; Equity Lab</h1><p>Exploring outpatient access, attendance and digital inclusion using an auditable, entirely synthetic data pipeline.</p></header>
<main><aside class='alert' role='note'><strong>Synthetic demonstration only.</strong> Every record and distribution in this report is invented. No NHS patient data. No official referral-to-treatment (RTT) calculations. Differences between groups do not establish causality.</aside>
<div class='cards'>{cards}</div>{''.join(sections)}<section><h2>Interpretation guardrails</h2><p>Attendance rates use all appointments as denominator. Waiting duration here is simply days from simulated referral to simulated appointment, not an NHS RTT waiting time. Small groups are suppressed. Segment comparisons are descriptive and should trigger consultation with patients and staff, not automated decisions about individuals.</p><p>Design follows the principle that digital channels should complement, not replace, accessible non-digital services.</p></section>
<footer>Synthetic test harness for the validation, quarantine and suppression logic. The real-data analysis is in the main report. Not affiliated with or endorsed by the NHS. Generated by the nhs-access-equity-lab codebase.</footer></main></body></html>"""
    output.write_text(html, encoding="utf-8")
