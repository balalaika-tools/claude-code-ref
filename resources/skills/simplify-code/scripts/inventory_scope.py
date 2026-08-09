#!/usr/bin/env python3
"""Build a deterministic, exclusion-aware inventory for simplification work."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    tomllib = None  # type: ignore[assignment]


DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "node_modules",
    "site-packages",
    "vendor",
    "vendored",
    "venv",
}

DEFAULT_EXCLUDED_PATTERNS = (
    "**/migrations/**",
    "**/snapshots/**",
    "**/__snapshots__/**",
    "**/*_generated.py",
    "**/generated/**",
)

CONFIG_NAME = ".simplify-code.json"


def run_git(root: Path, *args: str) -> tuple[list[str], str | None]:
    command = ["git", "-C", str(root), *args]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=False,
        )
    except OSError as exc:
        return [], f"could not run {' '.join(command[:3])}: {exc}"
    if result.returncode:
        detail = result.stderr.decode(errors="replace").strip()
        return [], f"{' '.join(command)} failed ({result.returncode}): {detail}"
    return [part.decode(errors="surrogateescape") for part in result.stdout.split(b"\0") if part], None


def resolve_root(value: str | None) -> Path:
    candidate = Path(value or ".").resolve()
    probe = subprocess.run(
        ["git", "-C", str(candidate), "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    if probe.returncode == 0:
        return Path(probe.stdout.strip()).resolve()
    return candidate


def load_json(path: Path) -> tuple[Any, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, f"could not read {path}: {exc}"


def load_config(root: Path, explicit: str | None) -> tuple[dict[str, Any], list[str]]:
    path = Path(explicit).resolve() if explicit else root / CONFIG_NAME
    if not path.exists():
        return {}, []
    data, error = load_json(path)
    if error:
        return {}, [error]
    if not isinstance(data, dict):
        return {}, [f"configuration must be a JSON object: {path}"]
    return data, []


def load_manifest(path: Path) -> tuple[list[str], list[str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [], [f"could not read manifest {path}: {exc}"]
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            return [], [f"invalid JSON manifest {path}: {exc}"]
        if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
            return [], [f"JSON manifest must be an array of paths: {path}"]
        return data, []
    return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")], []


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def matches_pattern(relative: str, pattern: str) -> bool:
    return fnmatch.fnmatch(relative, pattern) or PurePosixPath(relative).match(pattern)


def exclusion_reason(path: Path, root: Path, patterns: Iterable[str]) -> str | None:
    relative = path.relative_to(root).as_posix()
    if any(part in DEFAULT_EXCLUDED_DIRS for part in path.relative_to(root).parts):
        return "excluded-directory"
    for pattern in (*DEFAULT_EXCLUDED_PATTERNS, *patterns):
        if matches_pattern(relative, pattern):
            return f"excluded-pattern:{pattern}"
    return None


def iter_python_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        if path.suffix == ".py":
            yield path
        return
    if not path.is_dir():
        return
    for current, directories, files in os.walk(path, followlinks=False):
        directories[:] = sorted(name for name in directories if name not in DEFAULT_EXCLUDED_DIRS)
        for filename in sorted(files):
            if filename.endswith(".py"):
                yield Path(current) / filename


def collect_files(
    root: Path,
    requested: Iterable[str],
    patterns: Iterable[str],
    max_files: int,
) -> tuple[list[Path], list[dict[str, str]], list[dict[str, str]], list[str], int]:
    files: dict[str, Path] = {}
    skipped: list[dict[str, str]] = []
    excluded: list[dict[str, str]] = []
    errors: list[str] = []

    for raw in requested:
        candidate = Path(raw)
        resolved = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
        if not is_within(resolved, root):
            errors.append(f"path is outside repository root: {raw}")
            continue
        if not resolved.exists():
            skipped.append({"path": raw, "reason": "missing"})
            continue
        found_any = False
        for file_path in iter_python_files(resolved):
            found_any = True
            reason = exclusion_reason(file_path, root, patterns)
            relative = file_path.relative_to(root).as_posix()
            if reason:
                excluded.append({"path": relative, "reason": reason})
                continue
            files[relative] = file_path
        if resolved.is_file() and not found_any:
            skipped.append({"path": resolved.relative_to(root).as_posix(), "reason": "not-python"})

    ordered = [files[key] for key in sorted(files)]
    omitted_count = max(0, len(ordered) - max_files)
    if omitted_count:
        ordered = ordered[:max_files]
    return ordered, skipped, excluded, errors, omitted_count


def count_lines(path: Path) -> tuple[int, str | None]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return sum(1 for _ in handle), None
    except (OSError, UnicodeError) as exc:
        return 0, f"could not read {path}: {exc}"


def package_name(path: Path, root: Path) -> str:
    parent = path.parent
    package_parts: list[str] = []
    while parent != root and (parent / "__init__.py").is_file():
        package_parts.append(parent.name)
        parent = parent.parent
    if package_parts:
        return ".".join(reversed(package_parts))
    relative = path.relative_to(root)
    return relative.parts[0] if len(relative.parts) > 1 else "."


def is_test_path(relative: str) -> bool:
    path = PurePosixPath(relative)
    return any(part in {"test", "tests"} for part in path.parts) or path.name.startswith("test_") or path.name.endswith("_test.py")


def pyproject_metadata(root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"path": None, "requires_python": None, "configured_tools": []}
    path = root / "pyproject.toml"
    if not path.is_file():
        return result
    result["path"] = path.relative_to(root).as_posix()
    if tomllib is None:
        result["error"] = "tomllib unavailable; use Python 3.11+ to inspect pyproject metadata"
        return result
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        result["error"] = str(exc)
        return result
    project = data.get("project", {})
    if isinstance(project, dict):
        result["requires_python"] = project.get("requires-python")
    tool = data.get("tool", {})
    if isinstance(tool, dict):
        result["configured_tools"] = sorted(str(name) for name in tool)
    return result


def changed_paths(root: Path, since: str | None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    paths: set[str] = set()
    commands = (
        [("diff", "--name-only", "--diff-filter=ACMRTUXB", "-z", since)]
        if since
        else [
            ("diff", "--name-only", "--diff-filter=ACMRTUXB", "-z"),
            ("diff", "--cached", "--name-only", "--diff-filter=ACMRTUXB", "-z"),
        ]
    )
    for command in commands:
        values, error = run_git(root, *command)
        paths.update(values)
        if error:
            errors.append(error)
    untracked, error = run_git(root, "ls-files", "--others", "--exclude-standard", "-z")
    paths.update(untracked)
    if error:
        errors.append(error)
    return sorted(paths), errors


def write_output(payload: dict[str, Any], output: str) -> None:
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if output == "-":
        sys.stdout.write(serialized)
    else:
        Path(output).write_text(serialized, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Files or directories relative to the repository root")
    parser.add_argument("--root", help="Repository root; defaults to the current Git root")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--changed-only", action="store_true", help="Use staged, unstaged, and untracked paths")
    scope.add_argument("--since", metavar="REF", help="Use paths changed since REF, including current worktree state")
    parser.add_argument("--manifest", help="Text or JSON file containing additional paths")
    parser.add_argument("--config", help=f"JSON config; defaults to <root>/{CONFIG_NAME} when present")
    parser.add_argument("--exclude", action="append", default=[], help="Additional root-relative glob; repeatable")
    parser.add_argument("--max-files", type=int, default=5000, help="Maximum files returned (default: 5000)")
    parser.add_argument("--output", default="-", help="Output JSON path or - for stdout")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = resolve_root(args.root)
    config, errors = load_config(root, args.config)
    config_excludes = config.get("exclude", [])
    if not isinstance(config_excludes, list) or not all(isinstance(item, str) for item in config_excludes):
        errors.append("configuration field 'exclude' must be an array of strings")
        config_excludes = []
    patterns = [*config_excludes, *args.exclude]
    requested = list(args.paths)
    mode = "explicit"
    if args.changed_only or args.since:
        requested, changed_errors = changed_paths(root, args.since)
        errors.extend(changed_errors)
        mode = "since" if args.since else "changed-only"
    if args.manifest:
        manifest_paths, manifest_errors = load_manifest(Path(args.manifest).resolve())
        had_requested_scope = bool(requested)
        requested.extend(manifest_paths)
        errors.extend(manifest_errors)
        mode = f"{mode}+manifest" if had_requested_scope else "manifest"
    if not requested and not (args.changed_only or args.since or args.manifest):
        requested = ["."]
        mode = "repository"
    if args.max_files < 1:
        errors.append("--max-files must be positive")
        args.max_files = 1

    files, skipped, excluded, collection_errors, omitted_count = collect_files(
        root, requested, patterns, args.max_files
    )
    errors.extend(collection_errors)
    records: list[dict[str, Any]] = []
    total_loc = 0
    for path in files:
        loc, error = count_lines(path)
        if error:
            errors.append(error)
        total_loc += loc
        relative = path.relative_to(root).as_posix()
        records.append(
            {
                "path": relative,
                "loc": loc,
                "package": package_name(path, root),
                "test": is_test_path(relative),
            }
        )

    payload = {
        "schema_version": 1,
        "root": str(root),
        "mode": mode,
        "requested": requested,
        "python": sys.version.split()[0],
        "pyproject": pyproject_metadata(root),
        "files": records,
        "totals": {
            "files": len(records),
            "loc": total_loc,
            "excluded": len(excluded),
            "skipped": len(skipped),
            "omitted": omitted_count,
        },
        "excluded": sorted(excluded, key=lambda item: (item["path"], item["reason"])),
        "skipped": sorted(skipped, key=lambda item: (item["path"], item["reason"])),
        "errors": errors,
        "complete": not errors and omitted_count == 0,
    }
    write_output(payload, args.output)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
