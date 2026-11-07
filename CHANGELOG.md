# Changelog

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
