#!/usr/bin/env python3
"""Deduplicate, suppress, baseline, budget, and rank simplification candidates."""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from pathlib import Path
from typing import Any

CONFIDENCE = {"low": 0, "medium": 1, "high": 2}
RISK = {"low": 0, "medium": 1, "high": 2}
DEFAULT_BUDGETS = {"design": 50, "quality": 50}


def load_json(path: Path) -> tuple[Any, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, f"could not read {path}: {exc}"


def write_json(payload: dict[str, Any], output: str) -> None:
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if output == "-":
        sys.stdout.write(serialized)
    else:
        Path(output).write_text(serialized, encoding="utf-8")


def findings_from_payload(data: Any, source: str) -> tuple[list[dict[str, Any]], list[str], bool]:
    if isinstance(data, list):
        raw = data
        complete = True
        reported_errors: list[Any] = []
    elif isinstance(data, dict) and isinstance(data.get("findings"), list):
        raw = data["findings"]
        complete = bool(data.get("complete", True))
        reported_errors = data.get("errors", []) if isinstance(data.get("errors", []), list) else []
    else:
        return [], [f"{source} must be a finding array or an object with a 'findings' array"], False
    findings: list[dict[str, Any]] = []
    errors = [f"{source}: {error}" for error in reported_errors]
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            errors.append(f"{source} finding {index} is not an object")
            continue
        missing = [key for key in ("fingerprint", "path", "line", "category", "confidence", "risk") if key not in item]
        if missing:
            errors.append(f"{source} finding {index} lacks: {', '.join(missing)}")
            continue
        if item["confidence"] not in CONFIDENCE or item["risk"] not in RISK:
            errors.append(f"{source} finding {index} has unknown confidence or risk")
            continue
        findings.append(dict(item))
    return findings, errors, complete


def baseline_fingerprints(path: Path) -> tuple[set[str], list[str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return set(), [f"could not read baseline {path}: {exc}"]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")}, []
    if isinstance(data, list):
        values = [item.get("fingerprint") if isinstance(item, dict) else item for item in data]
    elif isinstance(data, dict):
        raw = data.get("findings", data.get("fingerprints", []))
        values = [item.get("fingerprint") if isinstance(item, dict) else item for item in raw] if isinstance(raw, list) else []
    else:
        values = []
    fingerprints = {value for value in values if isinstance(value, str)}
    return fingerprints, [] if fingerprints or not values else [f"baseline contains no valid fingerprints: {path}"]


def load_config(path: str | None) -> tuple[dict[str, Any], list[str]]:
    if not path:
        return {}, []
    data, error = load_json(Path(path).resolve())
    if error:
        return {}, [error]
    if not isinstance(data, dict):
        return {}, [f"configuration must be a JSON object: {path}"]
    return data, []


def parse_budget(values: list[str]) -> tuple[dict[str, int], list[str]]:
    budgets = dict(DEFAULT_BUDGETS)
    errors: list[str] = []
    for value in values:
        name, separator, raw_limit = value.partition("=")
        try:
            limit = int(raw_limit)
        except ValueError:
            limit = -1
        if not separator or not name or limit < 0:
            errors.append(f"invalid budget '{value}'; expected category=nonnegative-integer")
            continue
        budgets[name] = limit
    return budgets, errors


def suppression_rules(config: dict[str, Any]) -> tuple[list[dict[str, str]], list[str]]:
    raw = config.get("suppressions", [])
    if not isinstance(raw, list):
        return [], ["configuration field 'suppressions' must be an array"]
    rules: list[dict[str, str]] = []
    errors: list[str] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            errors.append(f"suppression {index} must be an object")
            continue
        reason = item.get("reason")
        selectors = {key: value for key in ("fingerprint", "detector", "path", "category") if isinstance((value := item.get(key)), str)}
        if not isinstance(reason, str) or not reason.strip():
            errors.append(f"suppression {index} needs a non-empty rationale")
            continue
        if not selectors:
            errors.append(f"suppression {index} needs fingerprint, detector, path, or category")
            continue
        rules.append({**selectors, "reason": reason.strip()})
    return rules, errors


def matches_suppression(item: dict[str, Any], rule: dict[str, str]) -> bool:
    for key in ("fingerprint", "detector", "category"):
        if key in rule and item.get(key) != rule[key]:
            return False
    return "path" not in rule or fnmatch.fnmatch(str(item.get("path", "")), rule["path"])


def rank_score(item: dict[str, Any]) -> int:
    conceptual = int(item.get("conceptual_reduction", 1))
    surface = max(1, len(item.get("affected_files", [item.get("path")]) or []))
    verification_bonus = 1 if item.get("verification") else 0
    boundary_penalty = 2 if item.get("crosses_boundary") else 0
    return (
        conceptual * 4
        + CONFIDENCE[item["confidence"]] * 3
        + verification_bonus
        - RISK[item["risk"]] * 4
        - min(surface - 1, 5)
        - boundary_penalty
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="Analyzer JSON files")
    parser.add_argument("--baseline", help="JSON report or newline-delimited fingerprint baseline")
    parser.add_argument("--config", help="JSON suppression/ranking configuration")
    parser.add_argument("--min-confidence", choices=tuple(CONFIDENCE), default="low")
    parser.add_argument("--budget", action="append", default=[], help="Per-category budget, e.g. design=25")
    parser.add_argument("--max-total", type=int, default=100, help="Maximum findings returned")
    parser.add_argument("--output", default="-", help="Output JSON path or - for stdout")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config, errors = load_config(args.config)
    config_budgets = config.get("budgets", {})
    budget_values = list(args.budget)
    if isinstance(config_budgets, dict):
        budget_values = [f"{key}={value}" for key, value in config_budgets.items()] + budget_values
    elif config_budgets:
        errors.append("configuration field 'budgets' must be an object")
    budgets, budget_errors = parse_budget(budget_values)
    errors.extend(budget_errors)
    rules, suppression_errors = suppression_rules(config)
    errors.extend(suppression_errors)
    if args.max_total < 1:
        errors.append("--max-total must be positive")
        args.max_total = 1

    source_complete = True
    raw_findings: list[dict[str, Any]] = []
    for source in args.inputs:
        data, error = load_json(Path(source).resolve())
        if error:
            errors.append(error)
            source_complete = False
            continue
        findings, source_errors, complete = findings_from_payload(data, source)
        raw_findings.extend(findings)
        errors.extend(source_errors)
        source_complete = source_complete and complete and not source_errors

    baseline: set[str] = set()
    if args.baseline:
        baseline, baseline_errors = baseline_fingerprints(Path(args.baseline).resolve())
        errors.extend(baseline_errors)

    deduplicated: dict[str, dict[str, Any]] = {}
    duplicate_count = 0
    for item in raw_findings:
        item["rank_score"] = rank_score(item)
        fingerprint = str(item["fingerprint"])
        current = deduplicated.get(fingerprint)
        if current is None or item["rank_score"] > current["rank_score"]:
            if current is not None:
                duplicate_count += 1
            deduplicated[fingerprint] = item
        else:
            duplicate_count += 1

    baselined: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    below_confidence: list[dict[str, Any]] = []
    eligible: list[dict[str, Any]] = []
    minimum = CONFIDENCE[args.min_confidence]
    for item in deduplicated.values():
        if item["fingerprint"] in baseline:
            baselined.append(item)
            continue
        matched = next((rule for rule in rules if matches_suppression(item, rule)), None)
        if matched:
            suppressed.append({"fingerprint": item["fingerprint"], "reason": matched["reason"]})
            continue
        if CONFIDENCE[item["confidence"]] < minimum:
            below_confidence.append(item)
            continue
        eligible.append(item)

    eligible.sort(
        key=lambda item: (
            -item["rank_score"],
            -int(item.get("conceptual_reduction", 1)),
            -CONFIDENCE[item["confidence"]],
            RISK[item["risk"]],
            item["path"],
            item["line"],
        )
    )
    category_counts: dict[str, int] = {}
    included: list[dict[str, Any]] = []
    omitted_budget: list[dict[str, Any]] = []
    for item in eligible:
        category = str(item["category"])
        budget = budgets.get(category, args.max_total)
        if category_counts.get(category, 0) >= budget or len(included) >= args.max_total:
            omitted_budget.append(item)
            continue
        category_counts[category] = category_counts.get(category, 0) + 1
        included.append(item)

    payload = {
        "schema_version": 1,
        "findings": included,
        "counts": {
            "input": len(raw_findings),
            "deduplicated": len(deduplicated),
            "duplicates_removed": duplicate_count,
            "baselined": len(baselined),
            "suppressed": len(suppressed),
            "below_confidence": len(below_confidence),
            "omitted_by_budget": len(omitted_budget),
            "returned": len(included),
        },
        "baselined_fingerprints": sorted(item["fingerprint"] for item in baselined),
        "suppressed": sorted(suppressed, key=lambda item: item["fingerprint"]),
        "below_confidence_fingerprints": sorted(item["fingerprint"] for item in below_confidence),
        "omitted_by_budget_fingerprints": sorted(item["fingerprint"] for item in omitted_budget),
        "budgets": budgets,
        "errors": errors,
        "complete": source_complete and not errors and not omitted_budget,
        "notice": "Ranking prioritizes review; it does not prove a candidate is safe or authorize edits.",
    }
    write_json(payload, args.output)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
