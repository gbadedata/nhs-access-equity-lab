# Who misses NHS outpatient appointments?

[![CI](https://github.com/gbadedata/nhs-access-equity-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/gbadedata/nhs-access-equity-lab/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue) ![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen) ![Data](https://img.shields.io/badge/data-NHS%20England%20official%20statistics-005eb8)

An analysis of 150.3 million hospital outpatient appointments (NHS England, Hospital Outpatient Activity 2025-26) and 30 months of GP appointment data, written for the person who has to decide what to do about missed appointments: a service manager, not a statistician.

**Report:** [`reports/index.html`](reports/index.html) (also published to GitHub Pages by the workflow in `.github/workflows/pages.yml`).

Every number in the report is computed from the official files in `data/raw/`; none is typed in by hand. The pipeline checks each file's SHA-256 before it runs and reconciles its totals with the figures NHS England states in the publication text.

## What the data says

| | 2025-26 |
|---|---|
| Outpatient appointments | 150.3 million |
| Missed without notice (DNA) | 8.2 million (5.4%) |
| Cancelled by the hospital | 13.9 million (9.3%), 1.7 times the DNAs |
| Attendances with no recorded ethnicity | 18.9% |

1. **Hospital cancellations are the bigger problem.** They rose from 6.8% of appointments in 2015-16 to 9.3% in 2025-26, while DNAs fell from 6.6% to 5.4%. The hospital cancels 13.9% of London-commissioned appointments, against 5.6% in the South West.
2. **Missed appointments are concentrated.** Men aged 20-24 miss 13.8% of booked appointments; people in their late 70s about 3.5%. Black patients' DNA rate (8.8%) is 1.81 times the White rate (4.9%).
3. **The ethnicity gap is not yet a finding about ethnicity.** The Black, Asian and Mixed populations are younger than the White population (2021 Census medians 32, 32 and 19 against 43), DNA rates fall steeply with age, and the published tables cannot age-standardise. Nearly a fifth of attendances have no ethnicity recorded.
4. **Remote appointments are missed less** (first appointments: 4.3% by telephone or video, 7.0% in person), but patients, specialties and recording differ, so that is a reason to pilot and evaluate, not proof.
5. **Most variation between trusts is expected.** With plain binomial limits, 142 of 151 trusts look like outliers. Allowing for genuine between-trust variation (Spiegelhalter 2005), 8 do. The high ones are mostly mental health, community and children's trusts; the low ones look like recording practice.

## Why the numbers can be trusted

- **Reconciliation.** The provider-level file is summed back to the publication's headline (150,317,821 appointments; 8,151,086 DNAs) and the computed DNA proportion for every ethnic group matches NHS England's published figure. Tests fail if either drifts.
- **Integrity.** `data/raw/MANIFEST.json` records the URL, size and SHA-256 of each file. `python -m nhs_outpatients verify` refuses changed files.
- **Data-quality screens, reported rather than hidden.** Trusts with more than 5% of appointments recorded as "unknown outcome" are taken out of the comparison and listed. East London NHS Foundation Trust's 88,765 appointments all have an unknown outcome; a naive analysis would have ranked it best in England with a 0% DNA rate.
- **Publisher conventions handled explicitly.** `*` suppression is kept as missing, not zero. Provider and regional counts are multiples of 5 (national counts are exact). HES uses the 2010 deprivation index. Fifteen trust codes carry an undocumented `-X` suffix; fourteen match ODS once it is removed and one maps to a closed trust code.
- **Linkage through ODS.** Providers are identified as NHS trusts by joining to the ODS trust register, not by guessing from the code. A "codes starting with R are trusts" rule would have misclassified independent-sector sites that use new five-character codes.
- **49 tests**, standard library only.

## Run it

Python 3.11 or later. No packages to install.

```bash
python -m nhs_outpatients verify        # check every source file against MANIFEST.json
python -m nhs_outpatients               # writes reports/index.html, findings.json and tables/*.csv
python -m unittest discover -s tests -v
```

`reports/tables/` holds tidy CSVs of every chart for anyone who wants to rebuild them in Excel or Power BI.

## Repository map

| Path | What it is |
|---|---|
| `nhs_outpatients/` | The real-data analysis: loaders for HES, GPAD and ODS files, statistics, report |
| `nhs_outpatients/xlsx.py` | A standard-library `.xlsx` reader, tested cell-for-cell against openpyxl |
| `nhs_outpatients/stats.py` | Wilson intervals, ratio of proportions, funnel-plot overdispersion |
| `data/raw/` | The official files, unmodified, with `MANIFEST.json` |
| `reports/` | Generated report, findings and tables |
| `access_lab/` | A separate synthetic pipeline used to test validation, quarantine and small-number suppression logic (see below) |
| `docs/` | Methods, decision log, product brief, governance notes |

## Limits

- These are national aggregate statistics. They describe patterns, not individual patients, and cannot say why anyone missed an appointment.
- Nothing here is age-standardised or adjusted for need, specialty mix or trust type. The report says where that matters.
- The trust comparison uses DNAs as a share of appointments with a recorded outcome and pools all specialties. Trusts of different types should be compared with like.
- GP "video or online" appointments include asynchronous online consultations, where there is little to miss.
- Independent portfolio work. Not affiliated with or endorsed by NHS England.

## The synthetic pipeline (`access_lab`)

`python -m access_lab run --output build` generates seeded, fully synthetic appointment records with known, planted patterns, and runs them through a CSV data contract, reason-coded quarantine, a SQLite load with audit rows, and small-number suppression. It exists to test that machinery against inputs where the right answer is known. Its numbers are invented and are never mixed with the real analysis.

## Sources

- NHS England, [Hospital Outpatient Activity 2025-26](https://digital.nhs.uk/data-and-information/publications/statistical/hospital-outpatient-activity/2025-26), published 24 September 2026.
- NHS England, [Appointments in General Practice, September 2026](https://digital.nhs.uk/data-and-information/publications/statistical/appointments-in-general-practice/september-2026).
- NHS England Organisation Data Service, [NHS trusts (etr)](https://www.odsdatasearchandexport.nhs.uk/).
- ONS, [Ethnic group by age and sex, England and Wales: Census 2021](https://www.ons.gov.uk/peoplepopulationandcommunity/culturalidentity/ethnicity/articles/ethnicgroupbyageandsexenglandandwales/latest).
- NHS England, [Core20PLUS5 (adults)](https://www.england.nhs.uk/about/equality/equality-hub/national-healthcare-inequalities-improvement-programme/core20plus5/).
- Spiegelhalter D. J. (2005). Funnel plots for comparing institutional performance. *Statistics in Medicine* 24(8):1185-1202.

Data re-used under the Open Government Licence v3.0. Code: MIT.
