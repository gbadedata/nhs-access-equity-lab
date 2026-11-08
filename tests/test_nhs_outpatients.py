"""Tests for the real-data outpatient analysis.

Most assertions are pinned to numbers NHS England publishes in the text of its
releases, so a parsing mistake shows up as a failed reconciliation.
"""
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest

from nhs_outpatients import gpad, hes, sources
from nhs_outpatients.analysis import build
from nhs_outpatients.report import nice_name, render, write_tables
from nhs_outpatients.stats import funnel_limits, overdispersion, risk_ratio, wilson
from nhs_outpatients.xlsx import read_sheet, sheet_names


class StatsTests(unittest.TestCase):
    def test_wilson_reference_value(self):
        low, high = wilson(10, 100)
        self.assertAlmostEqual(low, 0.0552, places=4)
        self.assertAlmostEqual(high, 0.1744, places=4)

    def test_wilson_handles_zero_events(self):
        low, high = wilson(0, 50)
        self.assertEqual(low, 0)
        self.assertGreater(high, 0)

    def test_risk_ratio_and_interval(self):
        ratio, low, high = risk_ratio(20, 100, 10, 100)
        self.assertAlmostEqual(ratio, 2.0)
        self.assertLess(low, 2.0)
        self.assertGreater(high, 2.0)

    def test_no_overdispersion_gives_zero_tau(self):
        totals = [1000] * 20
        events = [50] * 20
        self.assertEqual(overdispersion(events, totals, 0.05)["tau2"], 0.0)

    def test_overdispersion_widens_limits(self):
        totals = [100_000] * 20
        events = [3000 + 250 * i for i in range(20)]
        result = overdispersion(events, totals, sum(events) / sum(totals))
        self.assertGreater(result["tau2"], 0)
        narrow, wide = funnel_limits(100_000, 0.05, 3.09), funnel_limits(100_000, 0.05, 3.09, result["tau2"])
        self.assertLess(wide[0], narrow[0])
        self.assertGreater(wide[1], narrow[1])

    def test_limits_bracket_target_and_stay_in_range(self):
        lower, upper = funnel_limits(50, 0.02, 3.09, 0.01)
        self.assertGreaterEqual(lower, 0.0)
        self.assertLess(lower, 0.02)
        self.assertGreater(upper, 0.02)
        self.assertLessEqual(upper, 1.0)

    def test_overdispersion_needs_units(self):
        with self.assertRaises(ValueError):
            overdispersion([1, 2], [10, 10], 0.1)


class SourceTests(unittest.TestCase):
    def test_all_files_match_manifest(self):
        self.assertTrue(all(r["ok"] for r in sources.verify(strict=False)))

    def test_tampered_file_is_refused(self):
        entry = sources.manifest()["files"]["ods_nhs_trusts"]
        original = (sources.ROOT / entry["path"]).read_bytes()
        try:
            (sources.ROOT / entry["path"]).write_bytes(original + b"\n")
            with self.assertRaises(ValueError):
                sources.verify()
        finally:
            (sources.ROOT / entry["path"]).write_bytes(original)


class XlsxReaderTests(unittest.TestCase):
    path = None

    @classmethod
    def setUpClass(cls):
        cls.path = sources.path_of("hes_report_tables")

    def test_sheet_names(self):
        self.assertIn("Summary Report 4", sheet_names(self.path))

    def test_known_cells(self):
        rows = read_sheet(self.path, "Summary Report 1")
        latest = next(r for r in rows if r and r[0] == "2025-26")
        self.assertEqual(latest[6], 150317821)

    def test_matches_openpyxl_when_available(self):
        try:
            import openpyxl
        except ImportError:
            self.skipTest("openpyxl not installed; reader verified against it during development")
        book = openpyxl.load_workbook(self.path, data_only=True)
        for name in sheet_names(self.path):
            mine = read_sheet(self.path, name)
            for r, row in enumerate(book[name].iter_rows(values_only=True)):
                for c, value in enumerate(row):
                    other = mine[r][c] if r < len(mine) and c < len(mine[r]) else None
                    if isinstance(value, float):
                        self.assertAlmostEqual(value, other)
                    else:
                        self.assertEqual(value, other)


class HesParsingTests(unittest.TestCase):
    def test_suppressed_cells_are_none_not_zero(self):
        text = ("REPORTING_PERIOD,GEOGRAPHY_LEVEL,ORGANISATION_CODE,ORGANISATION_DESCRIPTION,MEASURE_TYPE,MEASURE,MEASURE_VALUE\n"
                "2526,03.Provider,ZZZ,TEST TRUST,Attendance Summary by Gender,01.Attended-Female,100\n"
                "2526,03.Provider,ZZZ,TEST TRUST,Attendance Summary by Gender,04.DNA-Female,*\n")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pla.csv"
            path.write_text(text)
            org = hes.load_provider_level(path)[("03.Provider", "ZZZ")]
        self.assertIsNone(org.value("Attendance Summary by Gender", "04.DNA-Female"))
        self.assertEqual(org.outcome_cells_suppressed(), 1)
        self.assertEqual(org.outcomes()["appointments"], 100)

    def test_wrong_columns_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text("a,b\n1,2\n")
            with self.assertRaises(ValueError):
                hes.load_provider_level(path)


class FindingsTests(unittest.TestCase):
    findings = None

    @classmethod
    def setUpClass(cls):
        cls.findings = build()

    def test_headline_reconciles_with_publication(self):
        h = self.findings["headline"]
        self.assertTrue(h["matches_published_headline"])
        self.assertEqual(h["appointments"], 150_317_821)
        self.assertEqual(h["dna"], 8_151_086)

    def test_outcomes_sum_to_appointments(self):
        h = self.findings["headline"]
        self.assertEqual(sum(h[k] for k in hes.OUTCOMES), h["appointments"])

    def test_trend_matches_headline_year(self):
        latest = self.findings["trend"][-1]
        self.assertEqual(latest["year"], "2025-26")
        self.assertEqual(latest["appointments"], self.findings["headline"]["appointments"])
        self.assertAlmostEqual(self.findings["trend"][4]["dna_pct"], 6.16, places=2)  # 2019-20, published as 6.2%

    def test_ethnicity_reproduces_published_proportions(self):
        for group in self.findings["ethnicity"]["groups"]:
            self.assertAlmostEqual(group["dna_pct"], group["published_proportion_pct"], places=2)

    def test_ethnicity_recording_gap(self):
        self.assertAlmostEqual(self.findings["ethnicity"]["recording"]["missing_share"], 0.1888, places=3)

    def test_age_denominator_excludes_cancellations(self):
        row = self.findings["age_sex"][0]
        expected = 100 * row["male_dna"] / (row["male_attended"] + row["male_dna"])
        self.assertAlmostEqual(row["male_dna_pct"], expected)

    def test_unknown_outcome_trust_is_screened_not_ranked(self):
        providers = self.findings["providers"]
        screened = {r["name"] for r in providers["screened_out_unknown_outcomes"]}
        ranked = {r["name"] for r in providers["nhs_trusts"]}
        self.assertIn("EAST LONDON NHS FOUNDATION TRUST", screened)
        self.assertNotIn("EAST LONDON NHS FOUNDATION TRUST", ranked)

    def test_overdispersion_changes_the_story(self):
        providers = self.findings["providers"]
        self.assertEqual(providers["naive_outside_998"], 142)
        self.assertEqual((providers["above_998"], providers["below_998"]), (4, 2))

    def test_sensitivity_to_scale_is_reported(self):
        sensitivity = self.findings["providers"]["sensitivity_untransformed"]
        self.assertEqual(sensitivity["outside_998"], 8)
        self.assertEqual(len(sensitivity["flagged_only_untransformed"]), 2)

    def test_x_suffix_codes_link_to_ods(self):
        linked = {r["code"]: r["ods_code"] for r in self.findings["providers"]["nhs_trusts"]}
        self.assertEqual(linked.get("RJ1-X"), "RJ1")

    def test_gp_file_matches_publication_text(self):
        gp = self.findings["general_practice"]
        self.assertEqual(gp["latest_month"], "2026-09")
        self.assertEqual(round(gp["latest_total"] / 1e6, 1), 34.1)

    def test_report_and_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            render(self.findings, out / "index.html")
            write_tables(self.findings, out / "tables")
            html = (out / "index.html").read_text()
            self.assertIn("150.3m", html)
            self.assertIn("Five things to take from this", html)
            with (out / "tables" / "ethnicity.csv").open() as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), 5)


class GpadTests(unittest.TestCase):
    def test_dna_share_of_known_ignores_unknown(self):
        self.assertAlmostEqual(gpad.dna_share_of_known({"Attended": 90, "DNA": 10, "Unknown": 900}), 0.10)

    def test_unknown_columns_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.csv"
            path.write_text("A,B\n1,2\n")
            with self.assertRaises(ValueError):
                gpad.load(path)


class NamingTests(unittest.TestCase):
    def test_nice_name(self):
        self.assertEqual(nice_name("ALDER HEY CHILDREN'S NHS FOUNDATION TRUST"), "Alder Hey Children's NHS Foundation Trust")


if __name__ == "__main__":
    unittest.main()
