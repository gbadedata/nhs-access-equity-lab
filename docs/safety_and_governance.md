# Safety, governance and equity review

**Scope**: analysis of published, aggregate NHS England statistics (no patient-level records), plus a separate synthetic test harness. No patient-facing decisions, clinical recommendations or risk stratification.

## Data protection by design

- Source generator has synthetic appointment identifiers only (`SYN-A-*`). No NHS Number, patient name, address, postcode, date of birth or clinician ID.
- Public outputs remain synthetic. The small-cell threshold is illustrative, not a formal statistical disclosure-control assessment.
- The analysis reads only committed public files; it fetches nothing and transmits nothing.
- Published aggregates are already disclosure-controlled by NHS England (suppression and rounding). This project does not attempt to reverse either.
- An arbitrary `--input` flag does **not** mean it is approved for real health data. Do not load real patient data into this repo or publish it to GitHub.

## Illustrative risks and mitigations

| Risk | Potential harm | Prototype response | Real deployment requirement |
| --- | --- | --- | --- |
| Treating synthetic disparity as real | Poor commissioning decisions | Explicit synthetic banner and provenance | Valid real data, approved methodology and subject-matter review |
| DNA data taken as patient fault | Stigmatisation | No patient-level ranking, service-access lens | Co-design with service users, adjust for constraints and appointment types |
| Digital-first design excludes some patients | Worsened inequalities | Breakdown by channel/assisted booking; non-digital access described | Accessible services, user research, reasonable adjustments |
| Incorrect numerator/denominator | Misleading metrics | Named DNA definition and unit tests | Formal metric specification and independent assurance |
| Small-group inference | Loss of privacy | Group suppression under 10 | Full disclosure-control assessment, complementary suppression and governance |
| Confusing waiting duration with RTT | Incorrect regulatory reporting | Clear ‘not official RTT’ label | Operational RTT clock definitions and validated pathway data |

## NHS principle and risk management

The six NHS Constitution values inform how to interpret and discuss results. NHS England's guidance on inclusive digital healthcare emphasises preserving non-digital support alongside digital services. Any real NHS deployment must assess clinical safety standards and data-protection requirements, including DCB0129 / DCB0160 where applicable. A table of hypothetical risks is **not a formal clinical safety case**.

References: NHS Constitution (GOV.UK); NHS England digital inclusion framework; NHS Digital clinical risk management standards.
