# Data dictionary and validation contract

One row per synthetic outpatient appointment. Dates are ISO-8601 `YYYY-MM-DD`.

| Column | Type | Description |
| --- | --- | --- |
| `appointment_id` | string | unique `SYN-A-*` identifier |
| `site` | enum | North Clinic / Central Hospital / East Health Centre / Riverside Clinic |
| `specialty` | enum | Dermatology / Cardiology / Ophthalmology / Orthopaedics / ENT |
| `age_band` | enum | 18-39 / 40-59 / 60-74 / 75+; simulated categories |
| `booking_channel` | enum | Digital / Telephone / In person |
| `assisted_booking_needed` | enum | Yes / No; **invented input** |
| `referral_date` | date | synthetic original referral date |
| `appointment_date` | date | synthetic appointment date, must be on/after referral |
| `status` | enum | Attended / Did not attend / Patient cancelled / Hospital cancelled |
| `wait_days` | integer | derived days from referral to appointment |

Rejected rows carry explicit reasons in `quarantine.json`: missing field, invalid categorical value, invalid date, appointment before referral, duplicate ID or invalid synthetic ID. The pipeline loads a full snapshot (not a multi-file incremental CDC system); repeated ingestion replaces the current appointment table and adds an audit entry.

*Please do not rename or reinterpret these invented categories as official NHS data items.*
