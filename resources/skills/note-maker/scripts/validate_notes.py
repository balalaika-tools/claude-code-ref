#!/usr/bin/env python3
"""Validate mechanical parts of the note-maker writing contract."""

from __future__ import annotations

import argparse
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

NOTE_NAME = re.compile(r"^\d{2}_.+\.md$")
NUMBERED_HEADING = re.compile(r"^##\s+(?:\d+\.|[1-9]️⃣)\s+")
WHAT_YOU_NEED = re.compile(
    r"\*\*What you need \((\d+) (?:thing|things|input|inputs|item|items)\):\*\*",
    re.IGNORECASE,
)
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


def first_index(lines: list[str], predicate) -> int | None:
    return next((index for index, line in enumerate(lines) if predicate(line)), None)


def short_version_bounds(lines: list[str]) -> tuple[int, int] | None:
    start = first_index(lines, lambda line: line.strip() == "## The short version")
    if start is None:
        return None
    for index in range(start + 1, len(lines)):
        if lines[index].strip() == "---" or NUMBERED_HEADING.match(lines[index]):
            return start, index
    return start, len(lines)


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

    bounds = short_version_bounds(lines)
    if bounds is None:
        result.error("missing '## The short version'")
        validate_links(path, lines, result)
        return result

    short_start, short_end = bounds
    short_lines = lines[short_start:short_end]
    numbered_start = first_index(lines, lambda line: bool(NUMBERED_HEADING.match(line)))
    audience_index = first_index(
        lines, lambda line: line.strip().startswith("> **Who this is for**:")
    )

    if audience_index is None:
        result.error("missing '> **Who this is for**:' audience line")
    elif audience_index > short_start:
        result.error("audience line must appear before the short version")
    if numbered_start is not None and short_start > numbered_start:
        result.error("short version appears after the first numbered section")
    if short_end + 1 > 80:
        result.error(f"short version ends on line {short_end + 1}; maximum is line 80")
    if short_end - short_start > 40:
        result.error(f"short version is {short_end - short_start} lines; maximum is 40")

    need_match = next(
        (
            WHAT_YOU_NEED.search(line)
            for line in short_lines
            if WHAT_YOU_NEED.search(line)
        ),
        None,
    )
    need_index = None
    if need_match is None:
        result.error("short version needs counted '**What you need (N things):**'")
    else:
        need_index = next(
            i for i, line in enumerate(short_lines) if WHAT_YOU_NEED.search(line)
        )
        stop_index = next(
            (
                i
                for i in range(need_index + 1, len(short_lines))
                if short_lines[i].startswith("**The code:**")
                or short_lines[i].startswith("**Worked example:**")
            ),
            len(short_lines),
        )
        actual_items = sum(
            bool(NUMBERED_ITEM.match(line))
            for line in short_lines[need_index + 1 : stop_index]
        )
        expected_items = int(need_match.group(1))
        if actual_items != expected_items:
            result.error(
                f"What you need says {expected_items}, but enumerates {actual_items}"
            )

    code_index = next(
        (
            i
            for i, line in enumerate(lines)
            if line.strip().startswith("```") and i > short_start
        ),
        None,
    )
    worked_local_index = first_index(
        short_lines, lambda line: line.strip().startswith("**Worked example:**")
    )
    worked_index = (
        short_start + worked_local_index if worked_local_index is not None else None
    )
    baseline_index = code_index if code_index is not None else worked_index
    if baseline_index is None or baseline_index >= short_end:
        result.error(
            "short version needs runnable code or a concrete '**Worked example:**'"
        )
    else:
        deadline = min(80, max(1, math.ceil(total_lines * 0.15)))
        if baseline_index + 1 > deadline:
            result.error(
                f"first runnable/worked example is on line {baseline_index + 1}; "
                f"deadline is line {deadline} (line 80 or 15%, whichever is sooner)"
            )

    if code_index is not None and code_index < short_end:
        code_end = next(
            (
                i
                for i in range(code_index + 1, short_end)
                if lines[i].strip().startswith("```")
            ),
            None,
        )
        if code_end is None:
            result.error("short-version code fence is not closed")
        elif not 10 <= code_end - code_index - 1 <= 25:
            result.error(
                "short-version code must contain 10–25 lines; "
                f"found {code_end - code_index - 1}"
            )

    success_index = first_index(
        short_lines, lambda line: line.strip().startswith("**Success signal:**")
    )
    if success_index is None:
        result.error("short version is missing '**Success signal:**'")

    deferral_index = next(
        (
            i
            for i, line in enumerate(short_lines)
            if line.strip().startswith("**Not handled yet:**")
        ),
        None,
    )
    if deferral_index is None:
        result.error("short version is missing '**Not handled yet:**'")
    else:
        deferral_text = " ".join(short_lines[deferral_index:])
        if not MARKDOWN_LINK.search(deferral_text):
            result.error("Not handled yet must link each deferred concern forward")

    local_baseline_index = (
        baseline_index - short_start if baseline_index is not None else None
    )
    ordered_indices = [
        need_index,
        local_baseline_index,
        success_index,
        deferral_index,
    ]
    if all(
        index is not None for index in ordered_indices
    ) and ordered_indices != sorted(ordered_indices):
        result.error(
            "short version must order What you need → code/worked example → "
            "Success signal → Not handled yet"
        )

    prefix = lines[:short_start]
    if any(
        "Before reading" in line or re.match(r"^## Prerequisites", line)
        for line in prefix
    ):
        result.error(
            "prerequisites must be advisory and appear after the short version"
        )

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
    if "**Not handled yet:**" in "\n".join(
        lines
    ) and "> **Production:**" not in "\n".join(lines):
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
