"""Official source files: where each came from, and an integrity check before use."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "raw" / "MANIFEST.json"


def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def path_of(key: str) -> Path:
    return ROOT / manifest()["files"][key]["path"]


def verify(strict: bool = True) -> list[dict]:
    """Check every file against its recorded size and SHA-256."""
    results = []
    for key, entry in manifest()["files"].items():
        file = ROOT / entry["path"]
        if not file.exists():
            results.append({"key": key, "ok": False, "problem": "missing"})
            continue
        data = file.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        ok = digest == entry["sha256"] and len(data) == entry["bytes"]
        results.append({"key": key, "ok": ok, "problem": None if ok else "digest_or_size_mismatch"})
    if strict and not all(r["ok"] for r in results):
        bad = ", ".join(r["key"] for r in results if not r["ok"])
        raise ValueError(f"Source files failed integrity check: {bad}")
    return results
