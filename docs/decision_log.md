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

## Earlier decisions (v0.1)

001 synthetic-only data; 002 SQLite and the standard library; 003 quarantine rather than silent repair; 004 describe, do not infer cause; 005 do not label waiting time as RTT. 002 to 005 still stand. 001 is superseded by 006 for the analysis.
