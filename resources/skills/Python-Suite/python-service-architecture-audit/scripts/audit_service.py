#!/usr/bin/env python3
"""Static, high-confidence checks for a layered Python service package."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path

INTERNAL_FORBIDDEN = {
    "domain": {
        "adapters",
        "api",
        "application",
        "bootstrap",
        "db",
        "genai",
        "observability",
        "ports",
    },
    "ports": {"adapters", "api", "application", "bootstrap", "db", "genai", "observability"},
    "application": {"adapters", "api", "bootstrap", "db", "genai"},
    "db": {"adapters", "api", "application", "bootstrap", "genai"},
    "genai": {"adapters", "api", "bootstrap", "db"},
}
PURE_BOUNDARIES = {"application", "core", "domain", "ports"}
FORBIDDEN_EXTERNAL = {
    "boto3",
    "botocore",
    "fastapi",
    "langchain",
    "langchain_aws",
    "langchain_core",
    "langgraph",
    "opentelemetry",
    "pgvector",
    "psycopg",
    "sqlalchemy",
    "starlette",
}
GENERIC_COLLECTIONS = {
    Path("errors.py"),
    Path("constants.py"),
    Path("core/errors.py"),
    Path("core/constants.py"),
    Path("common/errors.py"),
    Path("common/constants.py"),
}
FRAMEWORK_PORT_NAMES = {
    "ainvoke",
    "astream",
    "checkpoint_ns",
    "configurable",
    "durability",
    "recursion_limit",
    "stream_mode",
}


@dataclass(frozen=True, order=True)
class Finding:
    path: str
    line: int
    message: str
    severity: str = "VIOLATION"


def imports(tree: ast.AST) -> list[tuple[str, int, int]]:
    found: list[tuple[str, int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((alias.name, 0, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.append((node.module or "", node.level, node.lineno))
    return found


def boundary_for(path: Path, root: Path) -> str | None:
    relative = path.relative_to(root)
    return relative.parts[0] if len(relative.parts) > 1 else None


def audit_file(path: Path, root: Path, package: str) -> list[Finding]:
    relative = path.relative_to(root)
    display = str(relative)
    owner = boundary_for(path, root)
    try:
        tree = ast.parse(path.read_text(), filename=str(path))
    except SyntaxError as exc:
        return [Finding(display, exc.lineno or 0, f"cannot parse module: {exc.msg}")]

    findings: list[Finding] = []
    for module, level, line in imports(tree):
        if level:
            findings.append(Finding(display, line, "relative import crosses an implicit boundary"))
            continue
        external_root = module.split(".", maxsplit=1)[0]
        if owner in PURE_BOUNDARIES and external_root in FORBIDDEN_EXTERNAL:
            findings.append(
                Finding(display, line, f"{owner} imports external technology {external_root}")
            )
        prefix = f"{package}."
        if owner in INTERNAL_FORBIDDEN and module.startswith(prefix):
            target = module.removeprefix(prefix).split(".", maxsplit=1)[0]
            if target in INTERNAL_FORBIDDEN[owner]:
                findings.append(Finding(display, line, f"{owner} imports outer boundary {target}"))

    if relative in GENERIC_COLLECTIONS:
        findings.append(Finding(display, 1, "generic root/core error or constant collection"))

    if owner == "ports":
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                names = {node.name, *(arg.arg for arg in node.args.args + node.args.kwonlyargs)}
                leaked = sorted(names & FRAMEWORK_PORT_NAMES)
                if leaked:
                    findings.append(
                        Finding(
                            display,
                            node.lineno,
                            f"port exposes framework control vocabulary: {', '.join(leaked)}",
                            "REVIEW",
                        )
                    )
    return findings


def audit(root: Path, package: str) -> list[Finding]:
    return sorted(
        finding
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts
        for finding in audit_file(path, root, package)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_root", type=Path)
    parser.add_argument("--package", help="Import package name; defaults to directory name")
    args = parser.parse_args()
    root = args.package_root.resolve()
    if not root.is_dir():
        parser.error(f"package root is not a directory: {root}")
    findings = audit(root, args.package or root.name)
    for finding in findings:
        print(f"{finding.severity} {finding.path}:{finding.line}: {finding.message}")
    violations = sum(item.severity == "VIOLATION" for item in findings)
    reviews = len(findings) - violations
    print(f"architecture audit: {violations} violation(s), {reviews} review notice(s)")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
