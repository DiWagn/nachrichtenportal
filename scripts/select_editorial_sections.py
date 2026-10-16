#!/usr/bin/env python3
"""Lossless category selection from the editorial original_markdown.

Reads a dated report JSON and emits Markdown. Never assembles article text from
stories[]; those records are metadata only.

Examples:
  python3 scripts/select_editorial_sections.py berichte/2026-10-16.json
  python3 scripts/select_editorial_sections.py berichte/2026-10-16.json --categories wissenschaft natur
"""
import argparse
import json
import re
from pathlib import Path

CATEGORIES = {
    "international": "Internationale Politik",
    "deutschland": "Deutschland",
    "europa": "Europa / EU",
    "wissenschaft": "Wissenschaft",
    "ki": "Aktuelle KI / KI-Modelle",
    "natur": "Natur und Umwelt",
}
SECTION_HEADING = re.compile(r"(?m)^# ([^\n]+)(?:\n|$)")
NUMBERED_HEADING = re.compile(r"(?m)^(#{1,3})[ \t]+[1-9][0-9]*\.[ \t]+(?=\S)")


def normalize_headings(markdown: str) -> str:
    return NUMBERED_HEADING.sub(r"\1 ", markdown)


def split_original(markdown: str):
    """Return (preamble, ordered sections), preserving source bytes exactly."""
    headings = list(SECTION_HEADING.finditer(markdown))
    if not headings:
        raise ValueError("No top-level Markdown headings found")
    preamble = markdown[:headings[0].start()]
    sections = []
    for i, match in enumerate(headings):
        end = headings[i + 1].start() if i + 1 < len(headings) else len(markdown)
        sections.append((match.group(1).strip(), markdown[match.start():end]))
    if preamble + "".join(section for _, section in sections) != markdown:
        raise AssertionError("Editorial content changed while splitting")
    return preamble, sections


def select(markdown: str, categories: set[str] | None = None) -> str:
    preamble, sections = split_original(markdown)
    if categories is None:
        return normalize_headings(markdown)
    unknown = categories - CATEGORIES.keys()
    if unknown:
        raise ValueError("Unknown categories: " + ", ".join(sorted(unknown)))
    chosen = set(CATEGORIES[k] for k in categories)
    retained = []
    for heading, text in sections:
        if heading in chosen:
            retained.append(text)
        elif heading not in CATEGORIES.values():
            # Preserve shared overview, evaluation, outlook and source notes.
            retained.append(text)
    return normalize_headings(preamble + "".join(retained))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--categories", nargs="+", choices=tuple(CATEGORIES))
    args = parser.parse_args()
    data = json.loads(args.report.read_text(encoding="utf-8"))
    original = data.get("original_markdown")
    if not isinstance(original, str) or not original.strip():
        parser.error("original_markdown is missing; refusing reconstructed stories")
    print(select(original, set(args.categories) if args.categories else None), end="")


if __name__ == "__main__":
    main()
