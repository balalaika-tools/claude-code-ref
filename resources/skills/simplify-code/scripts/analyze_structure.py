#!/usr/bin/env python3
"""Generate review candidates for structural Python simplification.

The output is evidence for human/agent review, never an auto-fix instruction.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Any

import inventory_scope

CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}
DETECTORS = {
    "abstract-single-implementation",
    "catch-log-reraise",
    "duplicate-implementation",
    "forwarding-class",
    "pass-through-function",
    "redundant-boolean-branch",
}


@dataclass
class FunctionRecord:
    path: str
    qualname: str
    node: ast.FunctionDef | ast.AsyncFunctionDef
    is_method: bool


@dataclass
class ClassRecord:
    path: str
    node: ast.ClassDef


class DefinitionCollector(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self.path = path
        self.functions: list[FunctionRecord] = []
        self.classes: list[ClassRecord] = []

    def visit_Module(self, node: ast.Module) -> None:
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.functions.append(FunctionRecord(self.path, item.name, item, False))
            elif isinstance(item, ast.ClassDef):
                self.visit_ClassDef(item)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.classes.append(ClassRecord(self.path, node))
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.functions.append(FunctionRecord(self.path, f"{node.name}.{item.name}", item, True))


def read_json(path: Path) -> tuple[Any, str | None]:
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


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:40].rstrip("-") or "simplify-structure"


def finding(
    *,
    path: str,
    line: int,
    end_line: int,
    detector: str,
    summary: str,
    evidence: list[str],
    counter_evidence: list[str],
    proposal: str,
    behavior_contract: list[str],
    confidence: str,
    risk: str,
    conceptual_reduction: int,
    affected_files: list[str] | None = None,
    verification: list[str] | None = None,
    crosses_boundary: bool = False,
    category: str = "design",
) -> dict[str, Any]:
    fingerprint = f"{path}:{line}|{category}|{slugify(summary)}"
    return {
        "fingerprint": fingerprint,
        "path": path,
        "line": line,
        "end_line": end_line,
        "category": category,
        "priority": "P3",
        "detector": detector,
        "summary": summary,
        "evidence": evidence,
        "counter_evidence": counter_evidence,
        "proposal": proposal,
        "behavior_contract": behavior_contract,
        "confidence": confidence,
        "risk": risk,
        "conceptual_reduction": conceptual_reduction,
        "affected_files": sorted(set(affected_files or [path])),
        "verification": verification or [],
        "crosses_boundary": crosses_boundary,
    }


def body_without_docstring(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.stmt]:
    body = list(node.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        return body[1:]
    return body


def callable_parameter_names(node: ast.FunctionDef | ast.AsyncFunctionDef, is_method: bool) -> list[str]:
    names = [arg.arg for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)]
    if node.args.vararg:
        names.append(node.args.vararg.arg)
    if node.args.kwarg:
        names.append(node.args.kwarg.arg)
    if is_method:
        names = [name for name in names if name not in {"self", "cls"}]
    return names


def callable_parameters(node: ast.FunctionDef | ast.AsyncFunctionDef, is_method: bool) -> set[str]:
    return set(callable_parameter_names(node, is_method))


def direct_argument_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Starred) and isinstance(node.value, ast.Name):
        return node.value.id
    return None


def receiver_parameter(node: ast.expr) -> str | None:
    current = node
    while isinstance(current, ast.Attribute):
        current = current.value
    return current.id if isinstance(current, ast.Name) else None


def direct_forwarding_call(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    is_method: bool,
) -> ast.Call | None:
    body = body_without_docstring(node)
    if len(body) != 1:
        return None
    expression: ast.expr | None = None
    statement = body[0]
    if isinstance(statement, (ast.Return, ast.Expr)):
        expression = statement.value
    if isinstance(expression, ast.Await):
        expression = expression.value
    if not isinstance(expression, ast.Call):
        return None

    parameters = callable_parameters(node, is_method)
    forwarded: list[str] = []
    for argument in expression.args:
        name = direct_argument_name(argument)
        if name is None:
            return None
        forwarded.append(name)
    for keyword in expression.keywords:
        name = direct_argument_name(keyword.value)
        if name is None:
            return None
        forwarded.append(name)
    receiver = receiver_parameter(expression.func)
    if receiver in parameters:
        forwarded.append(receiver)
    if Counter(forwarded) != Counter(parameters):
        return None
    return expression


def dotted_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return "<dynamic call>"


def reference_counts(trees: dict[str, ast.Module]) -> tuple[Counter[str], Counter[str]]:
    all_refs: Counter[str] = Counter()
    test_refs: Counter[str] = Counter()
    for path, tree in trees.items():
        target = test_refs if inventory_scope.is_test_path(path) else None
        for node in ast.walk(tree):
            name = node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else None
            if name:
                all_refs[name] += 1
                if target is not None:
                    target[name] += 1
    return all_refs, test_refs


def detect_pass_through(
    functions: Iterable[FunctionRecord],
    refs: Counter[str],
    test_refs: Counter[str],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for record in functions:
        node = record.node
        if node.name.startswith("__") and node.name.endswith("__"):
            continue
        call = direct_forwarding_call(node, record.is_method)
        if call is None:
            continue
        target = dotted_name(call.func)
        if target.split(".")[-1] == node.name and not target.startswith(("self.", "cls.")):
            continue
        public = not node.name.startswith("_")
        decorated = bool(node.decorator_list)
        tests = test_refs[node.name]
        confidence = "low" if decorated or tests else "medium"
        risk = "high" if decorated else "medium" if public or isinstance(node, ast.AsyncFunctionDef) else "low"
        counter: list[str] = []
        if public:
            counter.append("The callable is public by naming convention; check downstream imports and compatibility.")
        if decorated:
            counter.append("Decorators may establish registration, policy, instrumentation, or a framework boundary.")
        if tests:
            counter.append(f"The symbol appears {tests} time(s) in test paths; inspect test-double or seam usage.")
        results.append(
            finding(
                path=record.path,
                line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                detector="pass-through-function",
                summary=f"Review pass-through callable {record.qualname}",
                evidence=[
                    f"The body contains one call to {target}.",
                    "Every non-receiver parameter is forwarded directly without transformation.",
                    f"The short symbol name has {refs[node.name]} static reference occurrence(s) in the analyzed scope.",
                ],
                counter_evidence=counter,
                proposal="If no policy, registration, instrumentation, or compatibility boundary exists, call the target directly and remove this layer.",
                behavior_contract=[
                    "Preserve argument binding and default behavior.",
                    "Preserve return/await behavior, exceptions, and side effects.",
                    "Preserve any public import or framework contract unless separately authorized.",
                ],
                confidence=confidence,
                risk=risk,
                conceptual_reduction=2,
                crosses_boundary=public or decorated,
                verification=["Inspect every caller and implementation before editing.", "Run focused tests covering this callable."],
            )
        )
    return results


def bool_constant_return(statement: ast.stmt) -> bool | None:
    if isinstance(statement, ast.Return) and isinstance(statement.value, ast.Constant) and isinstance(statement.value.value, bool):
        return statement.value.value
    return None


def detect_redundant_boolean(functions: Iterable[FunctionRecord]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for record in functions:
        for node in ast.walk(record.node):
            if not isinstance(node, ast.If) or len(node.body) != 1 or len(node.orelse) != 1:
                continue
            truthy = bool_constant_return(node.body[0])
            falsy = bool_constant_return(node.orelse[0])
            if truthy is None or falsy is None or truthy == falsy:
                continue
            direction = "bool(condition)" if truthy else "not bool(condition)"
            results.append(
                finding(
                    path=record.path,
                    line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    detector="redundant-boolean-branch",
                    summary=f"Collapse boolean branch in {record.qualname}",
                    evidence=["Both branches return opposite boolean constants and perform no other statements."],
                    counter_evidence=[],
                    proposal=f"Return {direction} directly if comments or branch breakpoints are not carrying useful intent.",
                    behavior_contract=["Return an exact bool.", "Evaluate the condition once.", "Preserve exception timing and side effects."],
                    confidence="high",
                    risk="low",
                    conceptual_reduction=1,
                    category="quality",
                    verification=["Run the focused tests for both truthy and falsy cases."],
                )
            )
    return results


def logged_call(statement: ast.stmt) -> str | None:
    if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
        return None
    target = dotted_name(statement.value.func)
    parts = target.lower().split(".")
    if any(part in {"log", "logger", "logging"} for part in parts) or parts[-1] in {
        "critical",
        "debug",
        "error",
        "exception",
        "info",
        "warning",
    }:
        return target
    return None


def detect_log_reraise(functions: Iterable[FunctionRecord]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for record in functions:
        for node in ast.walk(record.node):
            if not isinstance(node, ast.Try):
                continue
            for handler in node.handlers:
                if len(handler.body) != 2 or not isinstance(handler.body[1], ast.Raise) or handler.body[1].exc is not None:
                    continue
                logger = logged_call(handler.body[0])
                if not logger:
                    continue
                results.append(
                    finding(
                        path=record.path,
                        line=handler.lineno,
                        end_line=handler.end_lineno or handler.lineno,
                        detector="catch-log-reraise",
                        summary=f"Review log-and-reraise ownership in {record.qualname}",
                        evidence=[f"The handler calls {logger} and immediately re-raises the same exception."],
                        counter_evidence=["Logging is observable behavior and may establish required ownership or context."],
                        proposal="Trace outer handlers and observability requirements; if the same failure is logged again without added context, keep one deliberate logging owner.",
                        behavior_contract=["Preserve exception identity, traceback, and timing.", "Preserve required logs, metrics, and trace context."],
                        confidence="low",
                        risk="medium",
                        conceptual_reduction=1,
                        category="quality",
                        verification=["Exercise the failure path and inspect captured logging/telemetry."],
                    )
                )
    return results


def stored_dependency(node: ast.ClassDef) -> str | None:
    initializers = [item for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "__init__"]
    if len(initializers) != 1:
        return None
    stored: set[str] = set()
    for statement in ast.walk(initializers[0]):
        if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
            continue
        targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
        for target in targets:
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
                stored.add(target.attr)
    return next(iter(stored)) if len(stored) == 1 else None


def detect_forwarding_classes(
    classes: Iterable[ClassRecord],
    refs: Counter[str],
    test_refs: Counter[str],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for record in classes:
        node = record.node
        dependency = stored_dependency(node)
        if not dependency or node.bases or node.keywords:
            continue
        methods = [
            item
            for item in node.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name != "__init__"
        ]
        if len(methods) < 2:
            continue
        targets: list[str] = []
        all_forward = True
        for method in methods:
            call = direct_forwarding_call(method, True)
            target = dotted_name(call.func) if call else ""
            if call is None or not target.startswith(f"self.{dependency}."):
                all_forward = False
                break
            targets.append(target)
        if not all_forward:
            continue
        other_members = [
            item
            for item in node.body
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not (isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant) and isinstance(item.value.value, str))
        ]
        if other_members:
            continue
        public = not node.name.startswith("_")
        tests = test_refs[node.name]
        counter: list[str] = []
        if public:
            counter.append("The class is public by naming convention; inspect import and compatibility surfaces.")
        if tests:
            counter.append(f"The class appears {tests} time(s) in test paths; it may be a construction or test seam.")
        results.append(
            finding(
                path=record.path,
                line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                detector="forwarding-class",
                summary=f"Review forwarding class {node.name}",
                evidence=[
                    f"All {len(methods)} non-initializer methods delegate directly through self.{dependency}.",
                    f"Delegated targets: {', '.join(sorted(targets))}.",
                    f"The class name has {refs[node.name]} static reference occurrence(s) in the analyzed scope.",
                ],
                counter_evidence=counter,
                proposal="If the class owns no policy, lifecycle, instrumentation, alternate implementation, or public contract, inject/use the wrapped dependency directly.",
                behavior_contract=["Preserve construction and lifecycle.", "Preserve method signatures, exceptions, side effects, and instrumentation."],
                confidence="low" if public or tests else "medium",
                risk="high" if public else "medium",
                conceptual_reduction=4,
                crosses_boundary=public,
                verification=["Inspect every construction site, caller, test double, and registration mechanism."],
            )
        )
    return results


class LocalNameNormalizer(ast.NodeTransformer):
    def __init__(self, local_names: list[str]) -> None:
        self.mapping = {name: f"_local_{index}" for index, name in enumerate(local_names)}

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if node.id in self.mapping:
            node.id = self.mapping[node.id]
        return node

    def visit_arg(self, node: ast.arg) -> ast.AST:
        if node.arg in self.mapping:
            node.arg = self.mapping[node.arg]
        return node

    def visit_keyword(self, node: ast.keyword) -> ast.AST:
        self.generic_visit(node)
        if node.arg in self.mapping:
            node.arg = self.mapping[node.arg]
        return node


def function_signature(record: FunctionRecord) -> str | None:
    node = record.node
    body = body_without_docstring(node)
    if len(body) < 4 or (node.end_lineno or node.lineno) - node.lineno + 1 < 8:
        return None
    if any(isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) for item in ast.walk(ast.Module(body=body, type_ignores=[]))):
        return None
    local_names = callable_parameter_names(node, record.is_method)
    for item in ast.walk(ast.Module(body=body, type_ignores=[])):
        if isinstance(item, ast.Name) and isinstance(item.ctx, ast.Store) and item.id not in local_names:
            local_names.append(item.id)
    copied = copy.deepcopy(body)
    module = ast.Module(body=copied, type_ignores=[])
    normalized = LocalNameNormalizer(local_names).visit(module)
    payload = ast.dump(normalized, annotate_fields=True, include_attributes=False)
    kind = "async" if isinstance(node, ast.AsyncFunctionDef) else "sync"
    return hashlib.sha256(f"{kind}:{payload}".encode()).hexdigest()


def detect_duplicates(functions: Iterable[FunctionRecord]) -> list[dict[str, Any]]:
    groups: dict[str, list[FunctionRecord]] = defaultdict(list)
    for record in functions:
        signature = function_signature(record)
        if signature:
            groups[signature].append(record)
    results: list[dict[str, Any]] = []
    for records in groups.values():
        if len(records) < 2:
            continue
        records.sort(key=lambda item: (item.path, item.node.lineno, item.qualname))
        first = records[0]
        locations = [f"{item.path}:{item.node.lineno} ({item.qualname})" for item in records]
        affected = [item.path for item in records]
        crosses = len({PurePath(item.path).parts[0] for item in records}) > 1
        results.append(
            finding(
                path=first.path,
                line=first.node.lineno,
                end_line=first.node.end_lineno or first.node.lineno,
                detector="duplicate-implementation",
                summary=f"Review duplicate implementation around {first.qualname}",
                evidence=[
                    "Function bodies have identical AST structure after normalizing only parameters and assigned local names.",
                    f"Occurrences: {'; '.join(locations)}.",
                    "Constants, called functions, attributes, and control flow were preserved during comparison.",
                ],
                counter_evidence=["Structurally identical code may encode separate policies that should evolve independently."],
                proposal="Compare domain ownership and change history; share the canonical policy only when the occurrences must change together and no mini-framework is needed.",
                behavior_contract=["Preserve each caller's inputs, outputs, exceptions, and side effects.", "Do not couple distinct domain policies."],
                confidence="medium",
                risk="medium" if not crosses else "high",
                conceptual_reduction=min(5, len(records) + 1),
                affected_files=affected,
                crosses_boundary=crosses,
                category="quality",
                verification=["Run focused tests for every occurrence and caller after any consolidation."],
            )
        )
    return results


def base_names(node: ast.ClassDef) -> set[str]:
    return {dotted_name(base).split(".")[-1] for base in node.bases}


def is_abstract(node: ast.ClassDef) -> bool:
    if any(name in {"ABC", "ABCMeta"} or name.lower().startswith("abstract") for name in base_names(node)):
        return True
    return any(
        dotted_name(decorator).split(".")[-1] == "abstractmethod"
        for item in node.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        for decorator in item.decorator_list
    )


def detect_single_implementation(
    classes: Iterable[ClassRecord],
    refs: Counter[str],
    test_refs: Counter[str],
) -> list[dict[str, Any]]:
    records = list(classes)
    subclasses: dict[str, list[ClassRecord]] = defaultdict(list)
    for record in records:
        for base in base_names(record.node):
            subclasses[base].append(record)
    results: list[dict[str, Any]] = []
    for record in records:
        node = record.node
        implementations = subclasses.get(node.name, [])
        if not is_abstract(node) or len(implementations) != 1:
            continue
        implementation = implementations[0]
        tests = test_refs[node.name]
        public = not node.name.startswith("_")
        counter = ["Dynamic plugins or downstream packages may provide implementations outside the analyzed scope."]
        if tests:
            counter.append(f"The abstraction appears {tests} time(s) in test paths and may support test doubles.")
        if public:
            counter.append("The abstraction is public by naming convention and may stabilize a downstream contract.")
        results.append(
            finding(
                path=record.path,
                line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                detector="abstract-single-implementation",
                summary=f"Review single-implementation abstraction {node.name}",
                evidence=[
                    f"One implementation was found in scope: {implementation.node.name} at {implementation.path}:{implementation.node.lineno}.",
                    f"The abstraction name has {refs[node.name]} static reference occurrence(s) in the analyzed scope.",
                ],
                counter_evidence=counter,
                proposal="Keep the abstraction if it is a public, ownership, volatility, plugin, or test boundary; otherwise consider using the concrete implementation directly.",
                behavior_contract=["Preserve substitutability, test seams, registration, and public imports."],
                confidence="low",
                risk="high",
                conceptual_reduction=3,
                affected_files=[record.path, implementation.path],
                crosses_boundary=True,
                verification=["Inspect downstream imports, registrations, test doubles, and packaging entry points."],
            )
        )
    return results


def load_scope(args: argparse.Namespace) -> tuple[Path, list[Path], list[dict[str, str]], list[dict[str, str]], list[str], bool]:
    if args.inventory:
        data, error = read_json(Path(args.inventory).resolve())
        if error or not isinstance(data, dict):
            return Path(args.root or ".").resolve(), [], [], [], [error or "inventory must be an object"], False
        root = Path(str(data.get("root", args.root or "."))).resolve()
        records = data.get("files", [])
        files = [root / item["path"] for item in records if isinstance(item, dict) and isinstance(item.get("path"), str)]
        return root, files, data.get("skipped", []), data.get("excluded", []), list(data.get("errors", [])), bool(data.get("complete", False))

    root = inventory_scope.resolve_root(args.root)
    config, errors = inventory_scope.load_config(root, args.config)
    excludes = config.get("exclude", []) if isinstance(config.get("exclude", []), list) else []
    requested = args.paths or ["."]
    files, skipped, excluded, collection_errors, omitted = inventory_scope.collect_files(
        root, requested, [*excludes, *args.exclude], args.max_files
    )
    errors.extend(collection_errors)
    return root, files, skipped, excluded, errors, not errors and omitted == 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Python files or directories")
    parser.add_argument("--inventory", help="Inventory JSON from inventory_scope.py")
    parser.add_argument("--root", help="Repository root")
    parser.add_argument("--config", help="Optional .simplify-code.json path")
    parser.add_argument("--exclude", action="append", default=[], help="Additional exclusion glob")
    parser.add_argument("--disable", action="append", default=[], choices=sorted(DETECTORS), help="Disable a detector")
    parser.add_argument("--limit-per-detector", type=int, default=50, help="Result budget per detector")
    parser.add_argument("--max-files", type=int, default=5000, help="Maximum directly collected files")
    parser.add_argument("--output", default="-", help="Output JSON path or - for stdout")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit_per_detector < 1:
        raise SystemExit("--limit-per-detector must be positive")
    root, files, skipped, excluded, errors, scope_complete = load_scope(args)
    config, config_errors = inventory_scope.load_config(root, args.config)
    errors.extend(config_errors)
    configured_disabled = config.get("disabled_detectors", [])
    if not isinstance(configured_disabled, list) or not all(item in DETECTORS for item in configured_disabled):
        if configured_disabled:
            errors.append("configuration field 'disabled_detectors' must contain known detector names")
        configured_disabled = []
    disabled = set(args.disable) | set(configured_disabled)

    trees: dict[str, ast.Module] = {}
    functions: list[FunctionRecord] = []
    classes: list[ClassRecord] = []
    for path in files:
        try:
            relative = path.resolve().relative_to(root).as_posix()
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=relative, type_comments=True)
        except (OSError, UnicodeError, SyntaxError, ValueError) as exc:
            errors.append(f"could not parse {path}: {exc}")
            continue
        trees[relative] = tree
        collector = DefinitionCollector(relative)
        collector.visit(tree)
        functions.extend(collector.functions)
        classes.extend(collector.classes)

    refs, test_refs = reference_counts(trees)
    candidates_by_detector: dict[str, list[dict[str, Any]]] = {}
    detector_calls = {
        "pass-through-function": lambda: detect_pass_through(functions, refs, test_refs),
        "redundant-boolean-branch": lambda: detect_redundant_boolean(functions),
        "catch-log-reraise": lambda: detect_log_reraise(functions),
        "forwarding-class": lambda: detect_forwarding_classes(classes, refs, test_refs),
        "duplicate-implementation": lambda: detect_duplicates(functions),
        "abstract-single-implementation": lambda: detect_single_implementation(classes, refs, test_refs),
    }
    omitted: dict[str, int] = {}
    for name in sorted(DETECTORS):
        if name in disabled:
            continue
        produced = detector_calls[name]()
        if name == "pass-through-function":
            forwarding_ranges = [
                (item["path"], item["line"], item["end_line"])
                for item in candidates_by_detector.get("forwarding-class", [])
            ]
            produced = [
                item
                for item in produced
                if not any(
                    item["path"] == path and start <= item["line"] <= end
                    for path, start, end in forwarding_ranges
                )
            ]
        produced.sort(key=lambda item: (item["path"], item["line"], item["fingerprint"]))
        candidates_by_detector[name] = produced[: args.limit_per_detector]
        if len(produced) > args.limit_per_detector:
            omitted[name] = len(produced) - args.limit_per_detector

    candidates = [item for name in sorted(candidates_by_detector) for item in candidates_by_detector[name]]
    candidates.sort(
        key=lambda item: (
            -item["conceptual_reduction"],
            -CONFIDENCE_ORDER[item["confidence"]],
            item["path"],
            item["line"],
        )
    )
    payload = {
        "schema_version": 1,
        "root": str(root),
        "python": sys.version.split()[0],
        "files_analyzed": sorted(trees),
        "detectors_run": sorted(set(DETECTORS) - disabled),
        "detectors_disabled": sorted(disabled),
        "findings": candidates,
        "omitted": omitted,
        "skipped": skipped,
        "excluded": excluded,
        "errors": errors,
        "complete": scope_complete and not errors and not omitted,
        "notice": "Candidates require code reading and case-specific evidence; this report never authorizes edits.",
    }
    write_json(payload, args.output)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
