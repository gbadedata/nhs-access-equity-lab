"""CLI: python -m access_lab run --output build"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .generate import generate_rows, write_csv
from .metrics import build_metrics, write_metrics
from .pipeline import ingest
from .report import render


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthetic outpatient access and equity pipeline")
    parser.add_argument("command", choices=["run"])
    parser.add_argument("--rows", type=int, default=2400)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("build"))
    parser.add_argument("--input", type=Path, help="Optional replacement CSV with same schema; use synthetic data only")
    args = parser.parse_args()
    directory = args.output
    directory.mkdir(parents=True, exist_ok=True)
    source = args.input or directory / "synthetic_appointments.csv"
    if args.input is None:
        write_csv(generate_rows(args.rows, args.seed), source)
    result = ingest(source, directory / "appointments.sqlite", directory / "quarantine.json")
    metrics = build_metrics(directory / "appointments.sqlite")
    write_metrics(metrics, directory / "metrics.json")
    render(metrics, directory / "index.html")
    print(json.dumps({"ingestion": result, "report": str(directory / "index.html")}, indent=2))


if __name__ == "__main__":
    main()
