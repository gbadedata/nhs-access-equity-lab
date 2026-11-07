import csv
from datetime import date
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from access_lab.generate import FIELDS, generate_rows, write_csv
from access_lab.metrics import aggregate, build_metrics, percentile
from access_lab.pipeline import ingest, validate_row
from access_lab.report import render


class SyntheticGeneratorTests(unittest.TestCase):
    def test_seed_is_reproducible(self):
        self.assertEqual(generate_rows(20, 33), generate_rows(20, 33))

    def test_each_id_is_unique(self):
        items = generate_rows(200)
        self.assertEqual(len({r['appointment_id'] for r in items}), len(items))

    def test_no_real_personal_data_fields(self):
        self.assertNotIn('name', FIELDS)
        self.assertNotIn('nhs_number', FIELDS)
        self.assertNotIn('date_of_birth', FIELDS)

    def test_positive_row_count_required(self):
        with self.assertRaises(ValueError):
            generate_rows(0)

    def test_dates_in_order(self):
        for row in generate_rows(100):
            self.assertLessEqual(date.fromisoformat(row['referral_date']), date.fromisoformat(row['appointment_date']))


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.row = generate_rows(1)[0]

    def test_valid_row(self):
        value, error = validate_row(self.row)
        self.assertIsNone(error)
        self.assertGreaterEqual(value['wait_days'], 0)

    def test_missing_field(self):
        row = {**self.row, 'status': ''}
        self.assertEqual(validate_row(row)[1], 'missing_required_field')

    def test_invalid_status(self):
        self.assertEqual(validate_row({**self.row, 'status': 'Unknown'})[1], 'invalid_status_or_assistance')

    def test_invalid_calendar_date(self):
        self.assertEqual(validate_row({**self.row, 'referral_date': '2025-02-31'})[1], 'invalid_date')

    def test_backwards_wait(self):
        self.assertEqual(validate_row({**self.row, 'referral_date': '2099-01-01'})[1], 'appointment_before_referral')

    def test_non_synthetic_identifier(self):
        self.assertEqual(validate_row({**self.row, 'appointment_id': 'realpatient'})[1], 'invalid_synthetic_identifier')


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.csv = self.path / 'source.csv'
        self.db = self.path / 'dataset.db'
        self.quarantine = self.path / 'quarantine.json'

    def test_pipeline_generates_report(self):
        write_csv(generate_rows(100), self.csv)
        audit = ingest(self.csv, self.db, self.quarantine)
        self.assertEqual(audit['accepted_rows'], 100)
        self.assertEqual(audit['rejected_rows'], 0)
        metrics = build_metrics(self.db)
        render(metrics, self.path / 'index.html')
        text = (self.path / 'index.html').read_text()
        self.assertIn('Synthetic demonstration only', text)
        self.assertIn('Access &amp; Equity Lab', text)
        self.assertEqual(metrics['overall']['record_count'], 100)

    def test_invalid_and_duplicate_quarantined(self):
        rows = generate_rows(3)
        rows.append(rows[0].copy())
        rows.append({**rows[1], 'appointment_id': 'SYN-A-999999', 'status': 'Not real'})
        write_csv(rows, self.csv)
        audit = ingest(self.csv, self.db, self.quarantine)
        self.assertEqual((audit['accepted_rows'], audit['rejected_rows']), (3, 2))
        self.assertEqual({x['reason'] for x in json.loads(self.quarantine.read_text())},
                         {'duplicate_appointment_id', 'invalid_status_or_assistance'})

    def test_repeat_run_is_full_refresh(self):
        write_csv(generate_rows(5), self.csv)
        ingest(self.csv, self.db, self.quarantine)
        ingest(self.csv, self.db, self.quarantine)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute('select count(*) from appointment').fetchone()[0], 5)
            self.assertEqual(conn.execute('select count(*) from ingestion_audit').fetchone()[0], 2)

    def test_schema_mismatch_is_rejected(self):
        self.csv.write_text('id,other\n1,x\n')
        with self.assertRaises(ValueError):
            ingest(self.csv, self.db, self.quarantine)

    def test_suppression(self):
        write_csv(generate_rows(6), self.csv)
        ingest(self.csv, self.db, self.quarantine)
        value = build_metrics(self.db)['overall']
        self.assertTrue(value['suppressed'])
        self.assertIsNone(value['record_count'])


class MetricsTests(unittest.TestCase):
    def test_percentile_simple(self):
        self.assertEqual(percentile([0, 10], .9), 9)

    def test_empty_percentile(self):
        self.assertIsNone(percentile([], .9))

    def test_dna_denominator_is_all_appointments(self):
        base = {'wait_days': 14, 'status': 'Attended'}
        rows = [base] * 8 + [{**base, 'status': 'Did not attend'}] * 2
        self.assertEqual(aggregate(rows)['dna_percent_all_appointments'], 20.0)

    def test_minimum_display_cell(self):
        self.assertTrue(aggregate([{'status': 'Attended', 'wait_days': 1}], 10)['suppressed'])

    def test_invalid_minimum_cell(self):
        with self.assertRaises(ValueError):
            aggregate([], 0)


if __name__ == '__main__':
    unittest.main()

class SmallInputReportTests(unittest.TestCase):
    def test_report_can_render_suppressed_overall(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            source = path / 'data.csv'
            write_csv(generate_rows(2), source)
            db = path / 'data.sqlite'
            ingest(source, db, path / 'quarantine.json')
            render(build_metrics(db), path / 'index.html')
            self.assertIn('Suppressed', (path / 'index.html').read_text())
