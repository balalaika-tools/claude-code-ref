#!/usr/bin/env python3
"""Create a deterministic, non-overlapping worker plan from ranked findings."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

COORDINATOR_NAMES = {
    ".simplify-code.json",
    "conftest.py",
    "manage.py",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    "tox.ini",
}

RESULT_SCHEMA = {
    "shard": "string",
    "files_inspected": ["path"],
    "files_changed": ["path"],
    "applied": [{"id": "fingerprint", "summary": "string", "risk": "low|medium|high"}],
    "rejected": [{"id": "fingerprint", "reason": "string"}],
    "cross_shard": [{"file": "path", "proposal": "string"}],
    "checks": [{"command": "string", "result": "pass|fail|not-run"}],
    "uncertainty": ["string"],
}


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


def package_group(path: str, metadata: dict[str, dict[str, Any]]) -> str:
    record = metadata.get(path, {})
    package = str(record.get("package", ""))
    if package and package != ".":
        return package.split(".")[0]
    parts = PurePosixPath(path).parts
    return parts[0] if len(parts) > 1 else "root"


def coordinator_file(path: str) -> bool:
    pure = PurePosixPath(path)
    return pure.name in COORDINATOR_NAMES or pure.name == "__init__.py" or pure.suffix in {".toml", ".ini"}


def finding_files(item: dict[str, Any]) -> list[str]:
    values = item.get("affected_files")
    if isinstance(values, list):
        result = [value for value in values if isinstance(value, str)]
        if result:
            return sorted(set(result))
    path = item.get("path")
    return [path] if isinstance(path, str) else []


def is_cross_cutting(item: dict[str, Any], metadata: dict[str, dict[str, Any]]) -> bool:
    files = finding_files(item)
    groups = {package_group(path, metadata) for path in files}
    return (
        bool(item.get("crosses_boundary"))
        or item.get("risk") == "high"
        or len(groups) > 1
        or any(coordinator_file(path) for path in files)
    )


def related_tests(production: str, metadata: dict[str, dict[str, Any]]) -> list[str]:
    stem = PurePosixPath(production).stem
    candidates: list[tuple[int, str]] = []
    production_group = package_group(production, metadata)
    for path, record in metadata.items():
        if not record.get("test"):
            continue
        test_stem = PurePosixPath(path).stem
        if test_stem not in {f"test_{stem}", f"{stem}_test"}:
            continue
        same_group = package_group(path, metadata) == production_group
        candidates.append((0 if same_group else 1, path))
    return [path for _, path in sorted(candidates)]


def shard_weight(shard: dict[str, Any], metadata: dict[str, dict[str, Any]]) -> tuple[int, int, int]:
    files = {path for finding in shard["findings"] for path in finding_files(finding)}
    loc = sum(int(metadata.get(path, {}).get("loc", 0)) for path in files)
    return len(files), loc, len(shard["findings"])


def split_group(
    group: str,
    findings: list[dict[str, Any]],
    metadata: dict[str, dict[str, Any]],
    max_files: int,
    max_loc: int,
    max_findings: int,
) -> list[dict[str, Any]]:
    batches: list[dict[str, Any]] = []
    current: dict[str, Any] = {"group": group, "findings": []}
    for item in sorted(findings, key=lambda value: (-int(value.get("rank_score", 0)), value.get("path", ""), value.get("line", 0))):
        trial: dict[str, Any] = {"group": group, "findings": [*current["findings"], item]}
        file_count, loc, finding_count = shard_weight(trial, metadata)
        over_limit = file_count > max_files or loc > max_loc or finding_count > max_findings
        if current["findings"] and over_limit:
            batches.append(current)
            current = {"group": group, "findings": [item]}
        else:
            current = trial
    if current["findings"]:
        batches.append(current)
    return batches


def assign_files(shards: list[dict[str, Any]], metadata: dict[str, dict[str, Any]]) -> tuple[dict[str, str], list[str]]:
    owners: dict[str, str] = {}
    conflicts: set[str] = set()
    for shard in shards:
        shard_id = shard["id"]
        production_files = {
            path
            for finding in shard["findings"]
            for path in finding_files(finding)
            if not metadata.get(path, {}).get("test")
        }
        owned = {path for finding in shard["findings"] for path in finding_files(finding)}
        for path in sorted(production_files):
            owned.update(related_tests(path, metadata))
        for path in sorted(owned):
            if coordinator_file(path):
                conflicts.add(path)
                continue
            previous = owners.get(path)
            if previous and previous != shard_id:
                conflicts.add(path)
            else:
                owners[path] = shard_id
    for path in conflicts:
        owners.pop(path, None)
    return owners, sorted(conflicts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("findings", help="Ranked findings JSON")
    parser.add_argument("inventory", help="Inventory JSON")
    parser.add_argument("--workers", type=int, default=3, help="Concurrent workers per wave, 1-3")
    parser.add_argument("--max-files", type=int, default=10, help="Soft file limit per shard")
    parser.add_argument("--max-loc", type=int, default=2000, help="Soft LOC limit per shard")
    parser.add_argument("--max-findings", type=int, default=25, help="Soft finding limit per shard")
    parser.add_argument("--allowed-risk", choices=("low", "medium", "high"), default="low")
    parser.add_argument("--output", default="-", help="Output JSON path or - for stdout")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    if not 1 <= args.workers <= 3:
        errors.append("--workers must be between 1 and 3 so the coordinator remains active")
        args.workers = min(3, max(1, args.workers))
    for name in ("max_files", "max_loc", "max_findings"):
        if getattr(args, name) < 1:
            errors.append(f"--{name.replace('_', '-')} must be positive")
            setattr(args, name, 1)

    finding_data, finding_error = load_json(Path(args.findings).resolve())
    inventory_data, inventory_error = load_json(Path(args.inventory).resolve())
    if finding_error:
        errors.append(finding_error)
    if inventory_error:
        errors.append(inventory_error)
    if not isinstance(finding_data, dict) or not isinstance(finding_data.get("findings"), list):
        errors.append("ranked findings input must be an object with a 'findings' array")
        finding_data = {"findings": [], "complete": False}
    if not isinstance(inventory_data, dict) or not isinstance(inventory_data.get("files"), list):
        errors.append("inventory input must be an object with a 'files' array")
        inventory_data = {"files": [], "complete": False}
    for label, data in (("findings", finding_data), ("inventory", inventory_data)):
        reported = data.get("errors", [])
        if isinstance(reported, list):
            errors.extend(f"{label}: {error}" for error in reported)

    metadata = {
        item["path"]: item
        for item in inventory_data["files"]
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    findings = [item for item in finding_data["findings"] if isinstance(item, dict)]
    cross_cutting = [item for item in findings if is_cross_cutting(item, metadata)]
    local = [item for item in findings if item not in cross_cutting]
    coordinator_files = {
        path
        for item in cross_cutting
        for path in finding_files(item)
    }

    # Exclusive ownership is file-based. If one finding makes a file coordinator-owned,
    # keep every finding touching that file with the coordinator as well.
    promoted = [
        item
        for item in local
        if any(path in coordinator_files for path in finding_files(item))
    ]
    cross_cutting.extend(promoted)
    local = [item for item in local if item not in promoted]

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in local:
        path = str(item.get("path", ""))
        grouped[package_group(path, metadata)].append(item)

    draft_shards: list[dict[str, Any]] = []
    for group in sorted(grouped):
        draft_shards.extend(
            split_group(group, grouped[group], metadata, args.max_files, args.max_loc, args.max_findings)
        )
    width = max(2, len(str(len(draft_shards))))
    for index, shard in enumerate(draft_shards, start=1):
        shard["id"] = f"{shard['group']}-{index:0{width}d}"

    owners, conflicts = assign_files(draft_shards, metadata)
    coordinator_files.update(conflicts)
    if conflicts:
        promoted = [
            item
            for shard in draft_shards
            for item in shard["findings"]
            if any(path in coordinator_files for path in finding_files(item))
        ]
        known = {item.get("fingerprint") for item in cross_cutting}
        cross_cutting.extend(item for item in promoted if item.get("fingerprint") not in known)
        for shard in draft_shards:
            shard["findings"] = [item for item in shard["findings"] if item not in promoted]
        draft_shards = [shard for shard in draft_shards if shard["findings"]]
        owners, related_conflicts = assign_files(draft_shards, metadata)
        coordinator_files.update(related_conflicts)
    for path in coordinator_files:
        owners.pop(path, None)

    shards: list[dict[str, Any]] = []
    for shard in draft_shards:
        owned_files = sorted(path for path, owner in owners.items() if owner == shard["id"])
        findings_for_worker = list(shard["findings"])
        checks = sorted(
            {
                check
                for item in findings_for_worker
                for check in item.get("verification", [])
                if isinstance(check, str)
            }
        )
        loc = sum(int(metadata.get(path, {}).get("loc", 0)) for path in owned_files)
        shards.append(
            {
                "id": shard["id"],
                "group": shard["group"],
                "owned_files": owned_files,
                "loc": loc,
                "finding_count": len(findings_for_worker),
                "soft_limit_exceeded": len(owned_files) > args.max_files or loc > args.max_loc or len(findings_for_worker) > args.max_findings,
                "worker_input": {
                    "shard": shard["id"],
                    "owned_files": owned_files,
                    "explicit_exclusions": sorted(coordinator_files),
                    "findings": findings_for_worker,
                    "constraints": [
                        "Inspect and edit only owned_files.",
                        "Return cross-shard needs without editing them.",
                        "Do not commit, revert, clean the worktree, or run repository-wide formatters.",
                        "Reject candidates whose evidence does not establish accidental complexity.",
                    ],
                    "behavior_boundaries": sorted(
                        {
                            contract
                            for item in findings_for_worker
                            for contract in item.get("behavior_contract", [])
                            if isinstance(contract, str)
                        }
                    ),
                    "allowed_risk": args.allowed_risk,
                    "targeted_checks": checks,
                    "required_result_schema": RESULT_SCHEMA,
                },
            }
        )

    waves = [
        [shard["id"] for shard in shards[index : index + args.workers]]
        for index in range(0, len(shards), args.workers)
    ]
    unassigned = sorted(
        path
        for item in local
        for path in finding_files(item)
        if path not in owners and path not in coordinator_files
    )
    payload = {
        "schema_version": 1,
        "strategy": {
            "workers_per_wave": args.workers,
            "wave_count": math.ceil(len(shards) / args.workers) if shards else 0,
            "soft_limits": {
                "files": args.max_files,
                "loc": args.max_loc,
                "findings": args.max_findings,
            },
        },
        "waves": waves,
        "shards": shards,
        "coordinator": {
            "owned_files": sorted(coordinator_files),
            "cross_cutting_findings": cross_cutting,
            "responsibilities": [
                "Resolve public, shared, configuration, and cross-package decisions.",
                "Deduplicate worker results and run integrated verification.",
                "Inspect the combined diff and preserve pre-existing changes.",
            ],
        },
        "ownership": dict(sorted(owners.items())),
        "unassigned_files": unassigned,
        "errors": errors,
        "complete": bool(finding_data.get("complete", False))
        and bool(inventory_data.get("complete", False))
        and not errors
        and not unassigned,
        "notice": "This plan proposes ownership only; it does not authorize delegation or edits.",
    }
    write_json(payload, args.output)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
