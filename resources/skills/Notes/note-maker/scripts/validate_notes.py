#!/usr/bin/env python3
"""Validate role-agnostic mechanical parts of the note-maker writing contract."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

NOTE_NAME = re.compile(r"^\d{2}_.+\.md$")
NUMBERED_HEADING = re.compile(r"^##\s+(?:\d+\.|[1-9]️⃣)\s+")
NUMBERED_ITEM = re.compile(r"^\s*\d+\.\s+")
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
PRESCRIPTIVE_MARKER = re.compile(r"(?:> \*\*Rule\*\*:|⚠️|❌|✅)")


@dataclass
class Result:
    path: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def collect_notes(paths: list[Path]) -> list[Path]:
    notes: set[Path] = set()
    for path in paths:
        if path.is_file():
            notes.add(path.resolve())
            continue
        if path.is_dir():
            notes.update(
                candidate.resolve()
                for candidate in path.rglob("*.md")
                if NOTE_NAME.match(candidate.name)
            )
            continue
        raise FileNotFoundError(path)
    return sorted(notes)


def visible_paragraph_count(lines: list[str]) -> int:
    paragraphs = 0
    in_code = False
    pending: list[str] = []

    def flush() -> None:
        nonlocal paragraphs
        text = " ".join(pending).strip()
        if len(text) >= 40:
            paragraphs += 1
        pending.clear()

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            flush()
            in_code = not in_code
            continue
        if in_code or not stripped:
            flush()
            continue
        if stripped.startswith(("#", ">", "- ", "* ")) or NUMBERED_ITEM.match(stripped):
            flush()
            continue
        pending.append(stripped)
    flush()
    return paragraphs


def validate_links(path: Path, lines: list[str], result: Result) -> None:
    for line_number, line in enumerate(lines, start=1):
        for target in MARKDOWN_LINK.findall(line):
            clean_target = target.split("#", 1)[0].strip()
            if (
                not clean_target
                or "://" in clean_target
                or clean_target.startswith("mailto:")
            ):
                continue
            if not (path.parent / clean_target).exists():
                result.error(
                    f"line {line_number}: linked file does not exist: {clean_target}"
                )


def validate_note(path: Path) -> Result:
    result = Result(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    total_lines = len(lines)

    if not any(
        line.strip().startswith("> **Who this is for**:") for line in lines
    ):
        result.error("missing '> **Who this is for**:' audience line")

    fence_lines = [
        line_number
        for line_number, line in enumerate(lines, start=1)
        if line.strip().startswith("```")
    ]
    if len(fence_lines) % 2:
        result.error(f"unclosed fenced code block near line {fence_lines[-1]}")

    if sum("> **Key insight**:" in line for line in lines) != 1:
        result.error("note must contain exactly one '> **Key insight**:'")

    if total_lines > 500 and not any(
        "<!-- length-justification:" in line for line in lines[:30]
    ):
        result.error(
            f"note is {total_lines} lines; split it or add a length justification"
        )

    if "> **Core:**" not in "\n".join(lines):
        result.warn("no '> **Core:**' altitude marker")
    if "**Not handled yet:**" in "\n".join(lines) and "> **Production:**" not in "\n".join(lines):
        result.warn(
            "deferred concerns exist but no '> **Production:**' altitude marker appears"
        )
    if re.search(
        r"\bedge cases?\b", "\n".join(lines), re.IGNORECASE
    ) and "> **Edge case:**" not in "\n".join(lines):
        result.warn("edge-case material appears without a '> **Edge case:**' marker")

    markers = sum(len(PRESCRIPTIVE_MARKER.findall(line)) for line in lines)
    paragraphs = visible_paragraph_count(lines)
    if markers > paragraphs * 2:
        result.warn(
            f"prescriptive density is high ({markers} markers, {paragraphs} explanatory paragraphs)"
        )

    validate_links(path, lines, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="Note files or directories")
    args = parser.parse_args()

    try:
        notes = collect_notes(args.paths)
    except FileNotFoundError as error:
        parser.error(f"path does not exist: {error}")

    if not notes:
        parser.error("no note files found")

    results = [validate_note(path) for path in notes]
    for result in results:
        status = "FAIL" if result.errors else "PASS"
        print(f"{status} {result.path}")
        for message in result.errors:
            print(f"  ERROR: {message}")
        for message in result.warnings:
            print(f"  WARN:  {message}")

    failures = sum(bool(result.errors) for result in results)
    print(f"\nChecked {len(results)} note(s); {failures} failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
