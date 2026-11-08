# Methods

## Sources and integrity

All inputs are official files downloaded on 2026-11-07 and committed unchanged under `data/raw/`. `MANIFEST.json` records each file's URL, landing page, size and SHA-256. `nhs_outpatients.sources.verify()` runs before every analysis and stops if any file differs.

| Key | File | Used for |
|---|---|---|
| `hes_provider_level` | HES Outpatient 2025-26 Provider Level Analysis (CSV, long format) | National headline, appointment type, regions, trusts |
| `hes_report_tables` | HES Outpatient 2025-26 Report Tables (XLSX) | Trend, age and sex, ethnicity, deprivation, specialties |
| `hes_ethnicity_imd` | HES Outpatient 2025-26 Ethnic Category and IMD data (CSV) | Share of attendances with no recorded ethnicity |
| `hes_metadata` | HES Outpatient 2025-26 Metadata (XLSX) | Definitions; confirms IMD 2010 |
| `gpad_national_overview` | Appointments in General Practice, September 2026, National Overview (CSV) | GP DNA rate by appointment mode, April 2024 to September 2026 |
| `ods_nhs_trusts` | ODS `etr` report (NHS trusts) | Identifying which HES providers are current NHS trusts |

## Reconciliation checks (tests fail if any breaks)

1. The 15 "Attendance Summary by Gender" measures for England sum to 150,317,821 appointments and 8,151,086 DNAs; rounded, these equal the publication's stated 150.3m, 116.9m, 8.2m and 5.4%.
2. The 2025-26 row of Summary Report 1 equals the same total.
3. DNA / all appointments for each ethnic group equals NHS England's published "Proportion of DNAs from all appointments".
4. The GPAD National Overview sums to 34.1m for September 2026, the figure the publication gives for appointments in GP appointment books. The 35.1m headline covers all recording across general practice and is a different scope.

## Definitions

| Measure | Numerator | Denominator | Why |
|---|---|---|---|
| DNA rate: headline, trend, ethnicity, region | DNAs | All appointments | Matches the HES publication |
| DNA rate: age and sex, appointment type, specialty | DNAs | Attended + DNA | These tables publish no cancellations |
| DNA rate: trust funnel | DNAs | Appointments with a recorded outcome | Trusts that send "unknown outcome" records are neither rewarded nor penalised |
| GP DNA rate | DNA | Attended + DNA | About 6% of GP appointments have an unknown status, varying by mode |
| First attendances per 100,000 | First attendances (in person + tele) | Decile population, as published | Crude; not age- or need-adjusted |

## Statistics

- **Intervals for proportions:** Wilson score.
- **Ratio to the White group:** ratio of two proportions with a Katz log-scale 95% interval. At these volumes the intervals are a few hundredths wide; the uncertainty that matters is systematic (age structure, missing ethnicity), not sampling.
- **Funnel plot:** target is the England rate p0. Rates go on the variance-stabilising arcsine-square-root scale, where the sampling variance is 1/(4n). z-scores are winsorised at the 10th and 90th percentiles and their mean square gives the overdispersion; the between-trust variance tau² is added to each trust's sampling variance (Spiegelhalter 2005, additive random effects, as used for proportions in NHS and CQC monitoring). Limits are `sin²(asin(sqrt(p0)) ± z·sqrt(1/(4n) + tau²))` with z = 1.96 and 3.09. Without tau², 142 of 151 trusts fall outside 99.8% limits, because limits for trusts with a million appointments are a few hundredths of a percentage point wide. With it, 6 do (4 above, 2 below).
- **Sensitivity:** the same model on the untransformed proportion scale puts 8 trusts outside the limits. The 2 extra (Herefordshire and Worcestershire Health and Care, Liverpool University Hospitals) are borderline and reported as such.
- **Trust selection:** providers with at least 10,000 appointments whose code (after removing an undocumented `-X` suffix) is a current NHS trust in ODS `etr`, and whose unknown-outcome share is at most 5%.

## Publisher conventions

- `*` marks a suppressed small count. It is stored as missing; provider totals treat it as zero and record how many cells were affected.
- All regional and provider counts in the PLA file are multiples of 5, with smallest non-zero value 10; national counts are exact. This is consistent with rounding for disclosure control.
- HES deprivation deciles use the 2010 Index of Multiple Deprivation (HES metadata).
- Female attendances in Summary Report 3 include maternity attendances.

## What would make this stronger

- Age-standardised DNA rates by ethnicity and deprivation, which need patient-level or finer published tables (for example via an approved HES extract or a local data warehouse).
- Comparison of trusts within type (acute, mental health, community, specialist).
- Specialty mix adjustment for the trust comparison.
- A pre-registered evaluation of any reminder or booking change, with in-person routes kept open.
