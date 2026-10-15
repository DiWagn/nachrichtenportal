#!/usr/bin/env python3
"""Validate report JSON structure without publishing or network access."""
import json
from pathlib import Path

directory = Path(__file__).resolve().parents[1] / "berichte"
if not directory.exists():
    print("Noch keine Berichte vorhanden.")
    raise SystemExit(0)

for path in sorted(directory.glob("*.json")):
    with path.open(encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, (dict, list)):
        raise ValueError(f"{path}: Erwartet JSON-Objekt oder Liste")
    if path.name != "index.json":
        from datetime import date
        date.fromisoformat(path.stem)
    print(f"OK: {path.name}")
print("Hinweis: Dies ist keine inhaltliche Quellen- oder Faktenprüfung.")
