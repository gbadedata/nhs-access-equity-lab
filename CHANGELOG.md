# Changelog

## 0.2.3 (2026-11-08)

- **Correction:** the trust comparison now uses DNAs / (attended + DNAs). 22 trusts report no cancellations to HES, and the v0.2.2 denominator (every recorded outcome, cancellations included) made their rates look higher. Against England, 6 trusts are now above the 99.8% limits and 6 below (v0.2.2: 4 and 2, kept as a sensitivity check).
- Trusts are now compared like with like: after allowing for patients' age (indirect standardisation, square-root-scale funnel) and against trusts of the same type in NHS England's ERIC 2025/26. Only 3 trusts stand out in the same direction on every view.
- New source file: ERIC 2025/26 trust data, added to the SHA-256 manifest; new `eric.py` loader that refuses unknown trust types.
- Report and README: like-for-like section, age-adjusted funnel chart, peer-group table, cancellation note. Funnel charts accept ratios as well as proportions. 66 tests.
- README: References section (funnel and overdispersion methods, Wilson and Katz intervals, the DNA rate definition, NHS England DNA guidance, MHSDS), with in-text links; `CITATION.cff` lists ERIC and the overdispersion paper.

## 0.2.2 (2026-11-08)

- Funnel plot overdispersion now uses the arcsine-square-root scale, as in Spiegelhalter's method for proportions: 6 trusts outside the 99.8% limits (4 above, 2 below), not 8. The untransformed result is kept as a sensitivity check that names the 2 borderline trusts.
- Funnel x-axis now says what it plots: appointments with a recorded outcome.
- README rebuilt: report screenshots (light and dark), findings table, verification table, architecture diagram, expected output, data sources, roadmap. Added `CITATION.cff`. 51 tests.

## 0.2.1 (2026-11-07)

- GitHub Actions updated to current major versions (Node 24).

## 0.2.0 (2026-11-07)

- New `nhs_outpatients` package: the analysis is now computed from NHS England's official HES Outpatient 2025-26 and GPAD files (committed with a SHA-256 manifest), replacing six hand-typed headline numbers.
- Reconciliation tests: rebuilds the publication's 150,317,821 appointments and 8,151,086 DNAs, and its published DNA proportion for every ethnic group.
- Findings on trend, age and sex, ethnicity (with recording gap and age-structure caveat), in-person versus remote, region, deprivation, and GP appointment mode.
- Trust funnel plot with Spiegelhalter overdispersion, providers linked through the ODS trust register, and a data-quality screen for unknown outcomes.
- Standard-library XLSX reader, tested cell-for-cell against openpyxl. Still no runtime dependencies.
- Accessible SVG charts with tooltips, data tables and dark mode; tidy CSVs for Excel or Power BI.
- Removed `real_nhs_access/`; the synthetic `access_lab/` remains as a test harness. 49 tests.

## 0.1.0

Synthetic outpatient pipeline; hand-transcribed headline figures.
