"""CLI: python -m nhs_outpatients [--output reports] | python -m nhs_outpatients verify"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import sources
from .analysis import build
from .report import render, write_tables

ROOT = Path(__file__).resolve().parents[1]


def _clean(value):
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean(v) for v in value]
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Outpatient access and equity analysis from official NHS files")
    parser.add_argument("command", nargs="?", default="run", choices=["run", "verify"])
    parser.add_argument("--output", type=Path, default=ROOT / "reports")
    args = parser.parse_args()
    if args.command == "verify":
        results = sources.verify(strict=False)
        print(json.dumps(results, indent=2))
        raise SystemExit(0 if all(r["ok"] for r in results) else 1)
    findings = build()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "findings.json").write_text(json.dumps(_clean(findings), indent=2) + "\n", encoding="utf-8")
    write_tables(findings, args.output / "tables")
    render(findings, args.output / "index.html")
    h = findings["headline"]
    print(f"{h['appointments']:,} appointments, DNA {h['dna_pct']:.2f}%. Report: {args.output / 'index.html'}")


if __name__ == "__main__":
    main()
