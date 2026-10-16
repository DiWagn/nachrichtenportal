#!/usr/bin/env python3
"""Validate the editorial source of truth for a dated news JSON.

Usage: python3 scripts/validate_editorial_report.py berichte/2026-10-16.json
No network access or external dependencies required.
"""
import argparse
import json
import re
from pathlib import Path

SECTION_NUMBER = re.compile(r"(?m)^(#{2,3})[ \t]+([1-9][0-9]*)\.[ \t]+(?=\S)")
REQUIRED_HEADINGS = (
    "Das Wichtigste im Überblick",
    "Gesamtbewertung",
    "Worauf in den nächsten Tagen zu achten ist",
    "Quellen und Verlässlichkeit",
)


def website_markdown(original: str) -> str:
    """Only strip section heading numbering; do not rewrite editorial prose."""
    return SECTION_NUMBER.sub(r"\1 ", original)


def validate(path: Path) -> None:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("date") != path.stem:
        raise ValueError("Report date and filename disagree")
    original = report.get("original_markdown")
    if not isinstance(original, str) or not original.strip():
        raise ValueError("Missing editorial original_markdown; never silently use stories")
    for heading in REQUIRED_HEADINGS:
        if heading.casefold() not in original.casefold():
            raise ValueError(f"Missing editorial section: {heading}")
    if not re.search(r"(?m)^\|.+\|\s*$", original):
        raise ValueError("Missing Markdown overview table")
    result = website_markdown(original)
    # Confirm that the transformation changed nothing else.
    matches = list(SECTION_NUMBER.finditer(original))
    pieces = []
    previous = 0
    for match in matches:
        pieces.append(original[previous:match.start()])
        pieces.append(match.group(1) + " ")
        previous = match.end()
    pieces.append(original[previous:])
    if "".join(pieces) != result:
        raise AssertionError("Unexpected editorial text transformation")
    print(f"PASS: {path}; {len(original)} original characters; "
          f"{len(matches)} numbered headings; text otherwise unchanged")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    validate(args.report)
