# Product brief: outpatient access and equity

## Problem statement

A health informatics graduate trainee is supporting outpatient service improvement. A proposal is made to encourage digital appointment booking. The operational benefits are plausible, but the team must understand whether some users require additional support and whether improvements are equitable.

## Stakeholders

Patients and carers; accessibility and digital-inclusion representatives; reception and booking teams; clinicians; operational managers; analytics and information governance colleagues.

## User stories and evidence

| Story | Acceptance evidence |
| --- | --- |
| As an operational manager, I want appointment status and wait indicators by site to identify questions for improvement | HTML report groups by site with a documented denominator |
| As a digital inclusion lead, I want to compare booking channels without removing non-digital routes | breakdown by channel and assisted-booking need; non-causal disclaimer |
| As a data quality analyst, I need invalid records to be traceable | reason-coded quarantine and source SHA-256 |
| As an information governance adviser, I need to keep this portfolio safe for public demonstration | synthetic identifiers only; small cell policy; explicit no-real-data contract |
| As a reviewer, I need to reproduce findings | seed, no-dependency CLI, test suite and source fixtures |

## Decision scenario for an NHS manager

A dashboard indicates a higher synthetic DNA share for patients who need assisted booking. The **incorrect response** would be to conclude that the patients are at fault, remove the telephone channel, or target individuals automatically. A more responsible response would be to consult patients and staff, verify data quality, investigate accessibility and transport barriers, test an improvement without withdrawing existing options, and monitor results.

This illustrates the joint application of NHS values, Applied Intellect (listening and awareness of users) and Creative Force (designing an evidence-based, inclusive service improvement).

## What version 0.2 added

- Official HES and GPAD files as the evidence base, with reconciliation to the published headline, trust comparison through ODS, and an overdispersion-adjusted funnel plot.

## What a further iteration could add

- Co-design outcomes with patients and administrative staff.
- Add role-based views, robust statistical disclosure controls, and audit/approval workflows if an authorised project with real data ever exists.
- Build a measured A/B or interrupted-time-series service-improvement study, subject to clinical and governance review.

None of the above requires tracking or disclosing individuals in this demonstration.
