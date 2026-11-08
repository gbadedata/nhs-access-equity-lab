# Decision log

## 006 (v0.2): Compute from official files, never transcribe

Version 0.1 typed six headline numbers into CSVs. Even where the numbers were right, mixing scopes crept in (the GP 35.1m headline beside percentages from the 34.1m appointment-book file). v0.2 commits the publisher's files with SHA-256 digests and derives every figure, so a reviewer can rerun the whole analysis offline.

## 007: Reconcile before analysing

The pipeline reproduces the publication's own totals and ethnicity proportions and the tests fail if it cannot. A parsing error then shows up as a failed reconciliation rather than as a plausible-looking wrong chart.

## 008: Screen trusts for outcome recording, and say so

A trust whose appointments have unknown outcomes would otherwise look like the best in England. Screened trusts are listed in the report.

## 009: Overdispersion-adjusted funnel limits

With very large denominators, binomial limits flag almost every trust. Spiegelhalter's additive random-effects adjustment separates the handful of unusual trusts from ordinary variation, which is the comparison a manager can act on.

## 010: Link providers through ODS, not code patterns

Independent-sector sites now carry five-character codes that can start with R. Joining to the ODS trust register is the reliable test of "is this an NHS trust".

## 011: Keep the synthetic pipeline, demoted to a test harness

The seeded generator plants known effects, so it is useful for testing quarantine and suppression logic and useless as evidence. It stays, clearly separated.

## 012 (v0.2.2): Overdispersion on the arcsine scale

v0.2.0 estimated tau² on the raw proportion scale and found 8 trusts outside the 99.8% limits. Spiegelhalter's method, as used for proportions in NHS and CQC monitoring, works on a variance-stabilising scale. On that scale 6 are outside. The untransformed result stays in the report as a sensitivity check, and the 2 trusts that depend on the choice are named as borderline.

## 013 (v0.2.3): Compare trusts on attended + DNA, not on every recorded outcome

v0.2.2 divided a trust's DNAs by every appointment with a recorded outcome, cancellations included. 22 of the 151 trusts report no cancellations to HES at all, while at a typical trust cancellations are about a fifth of appointments, so that denominator made those trusts look worse purely because of recording practice. DNAs / (attended + DNAs) is the definition UK official statistics use for comparing missed appointments, and it is the only one the age tables support. The v0.2.2 result stays in the findings as a sensitivity check and is reproduced exactly (4 above, 2 below).

## 014 (v0.2.3): Like-for-like trust comparison, with official trust types

Classifying trusts from their HES specialty mix was tried and rejected: community trusts that deliver acute-specialty clinics and acute trusts with little activity in the ten published specialties are misclassified. ERIC 2025/26 gives every trust NHS England's own type, and all 151 ranked trusts match it. Age is allowed for by indirect standardisation with the 11 age bands HES publishes for each trust. The minimum peer-group size for limits (8) was fixed before the ERIC data were loaded, so it could not be tuned to the result.

## Earlier decisions (v0.1)

001 synthetic-only data; 002 SQLite and the standard library; 003 quarantine rather than silent repair; 004 describe, do not infer cause; 005 do not label waiting time as RTT. 002 to 005 still stand. 001 is superseded by 006 for the analysis.
