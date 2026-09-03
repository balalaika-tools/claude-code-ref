#!/usr/bin/env python3
"""Deterministic validation for the observability skill package."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path
from types import SimpleNamespace

try:
    import yaml
except ImportError as exc:  # pragma: no cover - actionable environment failure
    raise SystemExit("PyYAML is required: install it before running validation") from exc


COLLECTOR_IMAGE = "otel/opentelemetry-collector-contrib:0.159.0"

# Every `gen_ai.*` string literal this package is allowed to use, pinned to the
# convention revision in references/compatibility.md. Rule 3 of SKILL.md says
# never invent a key inside a standard namespace; without this allowlist that
# rule is only an assertion. Adding a row is a deliberate act: check the key
# against the pinned revision first, and if it is not there, it belongs under
# `app.gen_ai.*` instead.
STANDARD_GENAI_ATTRIBUTES = {
    "gen_ai.agent.id",
    "gen_ai.agent.name",
    "gen_ai.conversation.compacted",
    "gen_ai.conversation.id",
    "gen_ai.data_source.id",
    "gen_ai.input.messages",
    "gen_ai.operation.name",
    "gen_ai.output.messages",
    "gen_ai.output.type",
    "gen_ai.provider.name",
    "gen_ai.request.max_tokens",
    "gen_ai.request.model",
    "gen_ai.request.reasoning.level",
    "gen_ai.request.seed",
    "gen_ai.request.stream",
    "gen_ai.request.temperature",
    "gen_ai.request.top_k",
    "gen_ai.request.top_p",
    "gen_ai.response.finish_reasons",
    "gen_ai.response.id",
    "gen_ai.response.model",
    "gen_ai.response.time_to_first_chunk",
    "gen_ai.system_instructions",
    "gen_ai.token.type",
    "gen_ai.tool.call.arguments",
    "gen_ai.tool.call.id",
    "gen_ai.tool.call.result",
    "gen_ai.tool.definitions",
    "gen_ai.tool.name",
    "gen_ai.tool.type",
    "gen_ai.usage.audio.input_tokens",
    "gen_ai.usage.audio.output_tokens",
    "gen_ai.usage.cache_read.input_tokens",
    "gen_ai.usage.cache_write.input_tokens",
    "gen_ai.usage.input_tokens",
    "gen_ai.usage.output_tokens",
    "gen_ai.usage.reasoning.output_tokens",
    "gen_ai.workflow.name",
}
# Standard event names, which share the namespace but are not attributes.
STANDARD_GENAI_EVENTS = {
    "gen_ai.client.operation.exception",
}
STANDARD_GENAI_METRICS = {
    "gen_ai.client.operation.duration",
    "gen_ai.client.operation.time_to_first_chunk",
    "gen_ai.client.operation.time_per_output_chunk",
    "gen_ai.client.token.usage",
    "gen_ai.execute_tool.duration",
    "gen_ai.invoke_agent.duration",
    "gen_ai.invoke_agent.inference_calls",
    "gen_ai.invoke_agent.tool_calls",
    "gen_ai.invoke_workflow.duration",
    "gen_ai.server.request.duration",
    "gen_ai.server.time_per_output_token",
    "gen_ai.server.time_to_first_token",
}


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def require_phrases(text: str, phrases: tuple[str, ...], *, context: str) -> None:
    for phrase in phrases:
        require(phrase in text, f"{context} missing {phrase}")


def find_quick_validator(explicit: Path | None) -> Path | None:
    """Locate the Codex skill-creator validator, or None if it is not installed.

    It is an optional external toolchain. Returning None keeps the ~800 lines of
    checks below runnable on a machine that has never seen Codex; requiring it
    made the mandatory upgrade step in compatibility.md impossible to satisfy,
    so it was skipped, so none of these checks ran.
    """
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        candidates.append(
            Path(codex_home)
            / "skills/.system/skill-creator/scripts/quick_validate.py"
        )
    candidates.append(
        Path.home()
        / ".codex/skills/.system/skill-creator/scripts/quick_validate.py"
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def run_official_validator(
    skill_root: Path, quick_validator: Path | None, *, required: bool
) -> list[str]:
    if quick_validator is None:
        message = (
            "official quick_validate.py not found; skipping it. "
            "Install Codex's skill-creator or pass --quick-validator PATH."
        )
        require(not required, message.replace("skipping it", "required"))
        return [message]
    result = subprocess.run(
        [sys.executable, str(quick_validator), str(skill_root)],
        check=False,
        capture_output=True,
        text=True,
    )
    require(
        result.returncode == 0,
        "official skill validator failed:\n" + result.stdout + result.stderr,
    )
    return []


def markdown_targets(text: str) -> set[str]:
    targets = set(re.findall(r"\[[^\]]*\]\(([^)]+\.md(?:#[^)]+)?)\)", text))
    targets.update(re.findall(r"`([^`\n]+\.md(?:#[^`\n]+)?)`", text))
    return targets


def validate_references(skill_root: Path) -> None:
    missing: list[str] = []
    for document in skill_root.rglob("*.md"):
        for target in markdown_targets(document.read_text(encoding="utf-8")):
            clean = target.split("#", 1)[0]
            if "://" in clean or clean.startswith("mailto:"):
                continue
            candidates = [
                (document.parent / clean).resolve(),
                (skill_root / clean).resolve(),
                *((parent / clean).resolve() for parent in skill_root.parents),
            ]
            if not any(candidate.is_file() for candidate in candidates):
                missing.append(f"{document.relative_to(skill_root)} -> {target}")
    require(not missing, "unresolved Markdown references:\n" + "\n".join(missing))


def validate_standard_genai_contract(skill_root: Path) -> None:
    metrics_path = skill_root / "references/metrics/genai.md"
    text = metrics_path.read_text(encoding="utf-8")
    declared = set(
        re.findall(
            r"create_histogram\(\s*[\"'](gen_ai\.[^\"']+)[\"']",
            text,
        )
    )
    unknown = sorted(declared - STANDARD_GENAI_METRICS)
    require(not unknown, f"unknown standard gen_ai.* metrics: {unknown}")
    require("gen_ai.workflow.duration" not in text, "deprecated workflow metric remains")
    for forbidden in ("cache_read", "cache_write", "reasoning"):
        require(
            f'(\"{forbidden}\", normalized[' not in text,
            f"standard token histogram still records {forbidden}",
        )
    require(
        '("input", normalized["input_tokens"])' in text
        and '("output", normalized["output_tokens"])' in text,
        "standard token histogram must record input and output totals",
    )
    literal_token_types = re.findall(
        r"[\"']gen_ai\.token\.type[\"']\s*:\s*[\"']([^\"']+)", text
    )
    require(
        set(literal_token_types) <= {"input", "output"},
        f"custom values used under gen_ai.token.type: {literal_token_types}",
    )
    model_recorder = text.split("def record_model_operation(", 1)[1].split(
        "\ndef ", 1
    )[0]
    require(
        "if value:" not in model_recorder
        and model_recorder.count("if value is not None:") >= 2,
        "token metric recorder must preserve explicit zero and suppress only None",
    )
    for recorder in (
        "record_tool_execution",
        "record_agent_invocation",
        "record_workflow_invocation",
    ):
        body = text.split(f"def {recorder}(", 1)[1].split("\ndef ", 1)[0]
        require(
            '"gen_ai.operation.name"' not in body,
            f"{recorder} adds undeclared gen_ai.operation.name metric attribute",
        )


def complete_python_blocks(document: Path) -> list[str]:
    text = document.read_text(encoding="utf-8")
    return re.findall(
        r"<!-- complete-python-template -->\s*```python\n(.*?)```",
        text,
        re.DOTALL,
    )


def validate_python(skill_root: Path) -> None:
    compiled_templates = 0
    for script in (skill_root / "scripts").glob("*.py"):
        compile(script.read_text(encoding="utf-8"), str(script), "exec")
    for document in skill_root.rglob("*.md"):
        for index, block in enumerate(complete_python_blocks(document), start=1):
            compile(block, f"{document}#complete-template-{index}", "exec")
            compiled_templates += 1
    require(compiled_templates > 0, "no complete Python template was compiled")


def validate_trace_budget_calculator(skill_root: Path) -> None:
    script = skill_root / "scripts/estimate_trace_budget.py"
    spec = importlib.util.spec_from_file_location("estimate_trace_budget", script)
    require(spec is not None and spec.loader is not None, "cannot load trace budget calculator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    decimal = module.Decimal
    estimate = module.estimate_trace_budget(
        traces_per_second=decimal("10"),
        average_spans_per_trace=decimal("5"),
        average_bytes_per_span=decimal("1000"),
        effective_retained_percentage=decimal("5"),
        decision_wait_seconds=decimal("30"),
        burst_factor=decimal("2"),
        cache_multiplier=decimal("10"),
    )
    require(estimate.daily_input_traces == 864_000, "daily input traces are wrong")
    require(estimate.daily_input_spans == 4_320_000, "daily input spans are wrong")
    require(estimate.daily_retained_traces == 43_200, "retained traces are wrong")
    require(estimate.daily_retained_spans == 216_000, "retained spans are wrong")
    require(estimate.daily_retained_bytes == 216_000_000, "retained bytes are wrong")
    require(
        estimate.minimum_active_trace_capacity == 600,
        "active trace capacity is wrong",
    )
    require(
        estimate.suggested_sampled_cache_lower_bound == 6_000
        and estimate.suggested_non_sampled_cache_lower_bound == 6_000,
        "decision cache lower bounds are wrong",
    )
    try:
        module.estimate_trace_budget(
            traces_per_second=decimal("10"),
            average_spans_per_trace=decimal("5"),
            average_bytes_per_span=decimal("1000"),
            effective_retained_percentage=decimal("101"),
            decision_wait_seconds=decimal("30"),
        )
    except ValueError:
        pass
    else:
        raise ValidationError("trace budget calculator accepts retention above 100%")


def validate_serializer_fixtures(skill_root: Path) -> None:
    document = skill_root / "references/tracing/genai/content_capture.md"
    blocks = complete_python_blocks(document)
    require(len(blocks) == 1, "expected one complete content serializer template")
    namespace: dict[str, object] = {}
    exec(compile(blocks[0], str(document), "exec"), namespace)

    system, captured, batch_size = namespace["serialize_chat_model_input"](
        [
            [{"role": "user", "content": "first"}],
            [{"role": "user", "content": "second"}],
        ],
        separate_system_instructions=False,
    )
    require(system is None, "ordinary chat history produced separate system instructions")
    require(batch_size == 2, "batched input size is incorrect")
    captured_messages = json.loads(captured)
    require(
        len(captured_messages) == 1
        and captured_messages[0]["parts"][0]["content"] == "first",
        "batched input merged independent conversations",
    )

    system, captured, batch_size = namespace["serialize_chat_model_input"](
        [
            {"role": "system", "content": "extract entities"},
            {"role": "user", "content": "actual chunk"},
            {"role": "assistant", "content": "prior answer"},
            {"role": "tool", "tool_call_id": "call-1", "content": "prior result"},
        ],
        separate_system_instructions=True,
    )
    require(batch_size == 1, "single conversation has an incorrect batch size")
    require(
        json.loads(system or "[]")
        == [{"type": "text", "content": "extract entities"}],
        "separate system instructions do not use the standard parts schema",
    )
    captured_messages = json.loads(captured)
    require(
        [message["role"] for message in captured_messages]
        == ["user", "assistant", "tool"],
        "system instructions were duplicated in the captured chat history",
    )

    system, captured, _ = namespace["serialize_chat_model_input"](
        [
            {"role": "system", "content": "stay in history"},
            {"role": "user", "content": "hello"},
        ],
        separate_system_instructions=False,
    )
    require(system is None, "chat-history system message produced a separate attribute")
    require(
        [message["role"] for message in json.loads(captured)] == ["system", "user"],
        "chat-history system message was removed for an API without a separate field",
    )

    first_message = SimpleNamespace(
        type="ai",
        content_blocks=[
            {"type": "text", "text": "choice one"},
            {"type": "image", "url": "https://example.invalid/image"},
        ],
        tool_calls=[{"id": "call-1", "name": "lookup", "args": {"id": 1}}],
        response_metadata={"finish_reason": "tool_calls"},
    )
    second_message = SimpleNamespace(
        type="ai",
        content="choice two",
        tool_calls=[],
        response_metadata={"stopReason": "stop"},
    )
    response = SimpleNamespace(
        generations=[
            [
                SimpleNamespace(message=first_message, generation_info={}),
                SimpleNamespace(message=second_message, generation_info={}),
            ]
        ]
    )
    outputs = json.loads(namespace["serialize_llm_result"](response))
    require(len(outputs) == 2, "independent generations were merged")
    require(
        outputs[0]["finish_reason"] == "tool_calls"
        and any(part["type"] == "image" for part in outputs[0]["parts"])
        and any(part["type"] == "tool_call" for part in outputs[0]["parts"]),
        "finish reason, multimodal part, or tool call was not preserved",
    )
    require(
        all(output.get("finish_reason") for output in outputs),
        "an output message omitted its schema-required finish reason",
    )

    native_json_message = SimpleNamespace(
        type="ai",
        content_blocks=[
            {
                "type": "non_standard",
                "value": {"type": "json", "json": {"entities": []}},
            }
        ],
        tool_calls=[],
        response_metadata={"finishReason": "end_turn"},
    )
    native_json_response = SimpleNamespace(
        generations=[[SimpleNamespace(message=native_json_message, generation_info={})]]
    )
    native_json_output = json.loads(namespace["serialize_llm_result"](native_json_response))[0]
    require(
        native_json_output["finish_reason"] == "end_turn"
        and native_json_output["parts"]
        == [{"type": "json", "json": {"entities": []}}],
        "provider finish-reason casing or native JSON block was lost",
    )

    observation_input = json.loads(
        namespace["serialize_observation_input"](
            [
                {"role": "system", "content": "extract entities"},
                {"role": "user", "content": "source text"},
            ]
        )
    )
    require(
        observation_input
        == [
            {"role": "system", "content": "extract entities"},
            {"role": "user", "content": "source text"},
        ],
        "text-only observation input is not projected to role/content",
    )
    structured_text_message = SimpleNamespace(
        type="ai",
        content='{"entities": []}',
        tool_calls=[],
        response_metadata={"finish_reason": "stop"},
    )
    structured_text_response = SimpleNamespace(
        generations=[
            [SimpleNamespace(message=structured_text_message, generation_info={})]
        ]
    )
    require(
        json.loads(
            namespace["serialize_observation_output"](
                structured_text_response, "json"
            )
        )
        == {"entities": []},
        "structured text output is not projected to its decoded JSON object",
    )
    empty_reasoning_message = SimpleNamespace(
        type="ai",
        content=[
            {"type": "reasoning", "content": ""},
            {"type": "text", "text": '{"entities": []}'},
        ],
        tool_calls=[],
        response_metadata={"finish_reason": "stop"},
    )
    empty_reasoning_response = SimpleNamespace(
        generations=[
            [SimpleNamespace(message=empty_reasoning_message, generation_info={})]
        ]
    )
    canonical_with_empty_reasoning = json.loads(
        namespace["serialize_llm_result"](empty_reasoning_response)
    )
    require(
        canonical_with_empty_reasoning[0]["parts"][0]
        == {"type": "reasoning", "content": ""},
        "empty provider reasoning was lost from the canonical output",
    )
    require(
        json.loads(
            namespace["serialize_observation_output"](
                empty_reasoning_response, "json"
            )
        )
        == {"entities": []},
        "empty reasoning prevented structured backend presentation",
    )
    nonempty_reasoning_message = SimpleNamespace(
        type="ai",
        content=[
            {"type": "reasoning", "content": "material"},
            {"type": "text", "text": '{"entities": []}'},
        ],
        tool_calls=[],
        response_metadata={"finish_reason": "stop"},
    )
    nonempty_reasoning_response = SimpleNamespace(
        generations=[
            [SimpleNamespace(message=nonempty_reasoning_message, generation_info={})]
        ]
    )
    require(
        json.loads(
            namespace["serialize_observation_output"](
                nonempty_reasoning_response, "json"
            )
        )
        == json.loads(namespace["serialize_llm_result"](nonempty_reasoning_response)),
        "non-empty reasoning did not force canonical backend fallback",
    )
    require(
        json.loads(
            namespace["serialize_observation_output"](native_json_response, "json")
        )
        == [native_json_output],
        "non-text observation output did not fall back to the canonical envelope",
    )

    fallback_output = json.loads(namespace["serialize_text_output"]("done", None))
    require(
        fallback_output[0]["finish_reason"] == "unknown",
        "missing framework finish reason does not use the documented fallback",
    )
    no_id = json.loads(
        namespace["serialize_messages"](
            [{"role": "assistant", "tool_calls": [{"name": "lookup", "args": {}}]}]
        )
    )[0]["parts"][-1]
    require("id" not in no_id, "optional tool-call ID is emitted as an empty value")
    tool_response = json.loads(
        namespace["serialize_messages"](
            [{"role": "tool", "tool_call_id": "call-1", "content": "sunny"}]
        )
    )[0]["parts"][0]
    require(
        tool_response
        == {"type": "tool_call_response", "id": "call-1", "response": "sunny"},
        "tool result is not represented by the standard response part",
    )


def yaml_blocks(document: Path) -> list[str]:
    return re.findall(
        r"```yaml\n(.*?)```", document.read_text(encoding="utf-8"), re.DOTALL
    )


def collector_yaml_blocks(skill_root: Path) -> list[tuple[str, str]]:
    """Every YAML block under collector/, labelled by file and position.

    Extracting only the block after `## Configuration` in production.md left the
    filter snippet, the Langfuse pipelines, the temporary policies, both
    dev/staging configs, and component.md entirely unchecked — which is how an
    invalid processor key survived in a copy-pasteable fence.
    """
    blocks: list[tuple[str, str]] = []
    for document in sorted((skill_root / "references/collector").glob("*.md")):
        for index, block in enumerate(yaml_blocks(document), start=1):
            blocks.append((f"{document.name}#yaml-{index}", block))
    require(blocks, "no Collector YAML blocks found")
    return blocks


def production_yaml(skill_root: Path) -> str:
    path = skill_root / "references/collector/production.md"
    text = path.read_text(encoding="utf-8")
    match = re.search(r"## Configuration.*?```yaml\n(.*?)```", text, re.DOTALL)
    require(match is not None, "production Collector YAML block not found")
    return match.group(1)


def validate_otlp_first_contract(skill_root: Path) -> None:
    """Keep executable Collector guidance push-only and OTLP-first."""
    skill_text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    require(
        "OTLP push is the default" in skill_text,
        "SKILL.md no longer declares the OTLP-first push contract",
    )

    collector_documents = list((skill_root / "references/collector").glob("*.md"))
    collector_text = "\n".join(
        document.read_text(encoding="utf-8") for document in collector_documents
    )
    require(
        re.search(r"(?m)^\s*(?:-\s+)?pull:\s*$", collector_text) is None,
        "Collector guidance contains a pull self-metrics reader",
    )
    require(
        re.search(r"(?m)^\s+prometheus:\s*$", collector_text) is None,
        "Collector guidance contains a Prometheus scrape exporter",
    )
    for forbidden in (":8888", ":8889"):
        require(
            forbidden not in collector_text,
            f"Collector guidance exposes legacy scrape port {forbidden}",
        )
    require(
        re.search(r"(?i)curl[^\n]*/metrics", collector_text) is None,
        "Collector guidance verifies telemetry through a scrape endpoint",
    )


def validate_collector_yaml(skill_root: Path) -> str:
    # Every block must at least be parseable YAML, wherever it lives.
    for label, block in collector_yaml_blocks(skill_root):
        try:
            candidate = yaml.safe_load(block)
        except yaml.YAMLError as exc:
            raise ValidationError(f"invalid YAML in {label}:\n{exc}") from exc
        if (
            isinstance(candidate, dict)
            and "receivers" in candidate
            and "pipelines" in candidate.get("service", {})
        ):
            validate_collector_self_telemetry(candidate, label)
            pipelines = candidate["service"]["pipelines"]
            if "attributes/drop_secrets" in candidate.get("processors", {}):
                drop_actions = candidate["processors"]["attributes/drop_secrets"].get(
                    "actions", []
                )
                deleted_keys = {
                    action.get("key")
                    for action in drop_actions
                    if action.get("action") == "delete"
                }
                for secret_key in (
                    "http.request.header.authorization",
                    "http.request.header.cookie",
                    "http.response.header.set_cookie",
                    "db.query.text",
                    "db.statement",
                    "user.email",
                ):
                    require(
                        secret_key in deleted_keys,
                        f"{label} universal redaction does not delete {secret_key}",
                    )
                for pipeline_name, pipeline in pipelines.items():
                    require(
                        "attributes/drop_secrets" in pipeline.get("processors", []),
                        f"{label} {pipeline_name} pipeline bypasses universal secret redaction",
                    )

    config_text = production_yaml(skill_root)
    parsed = yaml.safe_load(config_text)
    require(isinstance(parsed, dict), "production Collector config is not a mapping")
    exporters = parsed.get("exporters", {})
    require(
        "otlphttp/metrics" in exporters,
        "production config must use the OTLP-first metrics exporter",
    )
    metrics_pipeline = parsed.get("service", {}).get("pipelines", {}).get("metrics", {})
    require(
        "otlphttp/metrics" in metrics_pipeline.get("exporters", []),
        "production metrics pipeline must push through the OTLP metrics exporter",
    )
    processors = parsed.get("processors", {})
    email_actions = [
        action
        for action in processors.get("attributes/drop_secrets", {}).get("actions", [])
        if action.get("key") == "user.email"
    ]
    require(
        email_actions == [{"key": "user.email", "action": "delete"}],
        "user.email must be deleted by default",
    )
    validate_exception_detail_split(parsed)
    validate_environment_ownership(parsed)
    return config_text


def validate_collector_self_telemetry(parsed: dict, label: str) -> None:
    """Every complete Collector template has an observable, stable identity."""
    telemetry = parsed.get("service", {}).get("telemetry", {})
    resource = telemetry.get("resource", {})
    require(
        isinstance(resource, dict),
        f"{label} self-telemetry resource is not a mapping",
    )
    supported_resource_keys = {
        "attributes",
        "schema_url",
        "detectors",
        "detection/development",
    }
    legacy_keys = sorted(set(resource) - supported_resource_keys)
    require(
        not legacy_keys,
        f"{label} uses legacy inline self-telemetry resource attributes: "
        + ", ".join(legacy_keys),
    )
    attributes = resource.get("attributes")
    require(
        isinstance(attributes, list) and attributes,
        f"{label} must use service.telemetry.resource.attributes",
    )
    resource_attributes: dict[str, object] = {}
    for index, attribute in enumerate(attributes):
        require(
            isinstance(attribute, dict),
            f"{label} resource attribute #{index + 1} is not a mapping",
        )
        name = attribute.get("name")
        require(
            isinstance(name, str) and bool(name.strip()) and "value" in attribute,
            f"{label} resource attribute #{index + 1} needs name and value",
        )
        require(
            name not in resource_attributes,
            f"{label} repeats self-telemetry resource attribute {name}",
        )
        resource_attributes[name] = attribute["value"]
    require(
        isinstance(resource_attributes.get("service.name"), str)
        and bool(str(resource_attributes["service.name"]).strip()),
        f"{label} has no stable self-telemetry service.name",
    )
    require(
        isinstance(resource_attributes.get("deployment.environment.name"), str)
        and bool(str(resource_attributes["deployment.environment.name"]).strip()),
        f"{label} has no self-telemetry deployment.environment.name",
    )
    require(
        "service.instance.id" not in resource_attributes,
        f"{label} hard-codes service.instance.id; each Collector replica must keep "
        "the automatically generated instance identity",
    )
    require(
        "service.version" not in resource_attributes,
        f"{label} hard-codes service.version; the Collector image supplies it",
    )

    logs = telemetry.get("logs", {})
    require(
        str(logs.get("level", "")).lower() == "info",
        f"{label} self-logs must use the INFO baseline",
    )
    require(
        logs.get("encoding") in {"console", "json"},
        f"{label} self-logs must select console or json encoding explicitly",
    )

    metrics = telemetry.get("metrics", {})
    require(
        metrics.get("level") == "normal",
        f"{label} self-metrics must use the normal baseline",
    )
    readers = metrics.get("readers", [])
    require(
        isinstance(readers, list) and readers,
        f"{label} has no explicit self-metrics delivery reader",
    )
    for reader in readers:
        require(
            isinstance(reader, dict),
            f"{label} self-metrics reader is not a mapping",
        )
        require(
            "pull" not in reader and set(reader) == {"periodic"},
            f"{label} self-metrics must use only an OTLP periodic push reader",
        )
        periodic = reader.get("periodic")
        require(
            isinstance(periodic, dict),
            f"{label} periodic self-metrics reader is not a mapping",
        )
        timeout = periodic.get("timeout")
        require(
            type(timeout) is int and 1 <= timeout <= 10_000,
            f"{label} periodic self-metrics reader must pin a 1..10000 ms "
            "shutdown/export budget; deployments must also keep it "
            "comfortably below their platform termination grace period",
        )
        otlp = periodic.get("exporter", {}).get("otlp")
        require(
            isinstance(otlp, dict)
            and otlp.get("protocol") == "http/protobuf"
            and isinstance(otlp.get("endpoint"), str)
            and bool(otlp["endpoint"].strip()),
            f"{label} periodic self-metrics reader must push over OTLP/HTTP",
        )


def validate_exception_detail_split(parsed: dict) -> None:
    """Exception detail is deleted on traces only.

    errors.md moves exception detail out of spans and into correlated log
    records; deleting it on the logs pipeline removes the only copy.
    """
    processors = parsed.get("processors", {})
    for name, definition in processors.items():
        keys = {action.get("key") for action in definition.get("actions", [])}
        if not keys & {"exception.message", "exception.stacktrace"}:
            continue
        pipelines = parsed.get("service", {}).get("pipelines", {})
        for pipeline_name, pipeline in pipelines.items():
            require(
                not pipeline_name.startswith("logs")
                or name not in (pipeline.get("processors") or []),
                f"{name} deletes exception detail on the {pipeline_name} pipeline; "
                "the log record is where the stack trace lives",
            )


def validate_environment_ownership(parsed: dict) -> None:
    """A Collector must not overwrite an environment the application set."""
    for name, definition in parsed.get("processors", {}).items():
        if not name.startswith("resource"):
            continue
        for attribute in definition.get("attributes", []):
            if attribute.get("key") != "deployment.environment.name":
                continue
            require(
                attribute.get("action") == "insert",
                f"{name} uses action={attribute.get('action')!r} for "
                "deployment.environment.name; insert never overwrites the "
                "application's own value",
            )


MEASURED_TAIL_SAMPLING_KEYS = (
    "decision_wait",
    "num_traces",
    "expected_new_traces_per_sec",
    "sampled_cache_size",
    "non_sampled_cache_size",
    "threshold_ms",
    "min_value",
    "sampling_percentage",
)


def validate_measured_values_are_marked(skill_root: Path) -> None:
    """Every unmeasurable literal in production.md carries a `# MEASURE:` note.

    Four prose warnings elsewhere do not beat one syntactically valid YAML block
    an agent can paste. The values stay real numbers so the config can be
    image-validated; the marker is what stops them reading as defaults.
    """
    text = (skill_root / "references/collector/production.md").read_text(
        encoding="utf-8"
    )
    unmarked: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        key = stripped.split(":", 1)[0].strip()
        if key not in MEASURED_TAIL_SAMPLING_KEYS:
            continue
        if ":" not in stripped or not stripped.split(":", 1)[1].strip():
            continue
        if "# MEASURE:" not in line:
            unmarked.append(stripped)
    require(
        not unmarked,
        "sampling values missing a `# MEASURE:` marker (they read as defaults):\n"
        + "\n".join(unmarked),
    )


COLLECTOR_CONFIG_KEYS = {
    "receivers",
    "processors",
    "exporters",
    "extensions",
    "connectors",
    "service",
}


def fragment_as_config(parsed: object) -> dict | None:
    """Wrap a partial snippet in the smallest config that exercises its schema.

    A fragment that is never handed to the binary is a fragment whose keys are
    never checked — which is how an invalid `filter` processor key survived in a
    copy-pasteable fence. Any pipeline block in the fragment is discarded and
    replaced, because it names components defined in a different fence.
    """
    # A bare list is a tail-sampling policy list; give it a host processor.
    if isinstance(parsed, list):
        return {
            "receivers": {"otlp": {"protocols": {"http": {}}}},
            "processors": {
                "tail_sampling": {
                    "decision_wait": "10s",
                    "num_traces": 100,
                    "policies": parsed,
                }
            },
            "exporters": {"debug": {}},
            "service": {
                "pipelines": {
                    "traces": {
                        "receivers": ["otlp"],
                        "processors": ["tail_sampling"],
                        "exporters": ["debug"],
                    }
                }
            },
        }

    if not isinstance(parsed, dict):
        return None
    # Not a Collector config at all — a Compose file, a Dockerfile snippet.
    if not set(parsed) <= COLLECTOR_CONFIG_KEYS:
        return None

    processors = dict(parsed.get("processors") or {})
    exporters = dict(parsed.get("exporters") or {})
    extensions = dict(parsed.get("extensions") or {})
    service_fragment = parsed.get("service") or {}
    telemetry = (
        service_fragment.get("telemetry")
        if isinstance(service_fragment, dict)
        else None
    )
    if not processors and not exporters and not extensions and telemetry is None:
        return None

    exporters.setdefault("debug", {})
    config: dict = {
        "receivers": {"otlp": {"protocols": {"http": {}}}},
        "exporters": exporters,
        "service": {
            "pipelines": {
                "traces": {
                    "receivers": ["otlp"],
                    "processors": list(processors),
                    "exporters": list(exporters),
                }
            }
        },
    }
    if processors:
        config["processors"] = processors
    if extensions:
        config["extensions"] = extensions
        config["service"]["extensions"] = list(extensions)
    if telemetry is not None:
        config["service"]["telemetry"] = telemetry
    return config


def validate_collector_image(skill_root: Path) -> None:
    environment = {
        "APM_ENDPOINT": "https://example.invalid/otel",
        "APM_AUTHORIZATION": "test",
        "PROMETHEUS_WRITE_ENDPOINT": "https://example.invalid/write",
        "PROMETHEUS_AUTHORIZATION": "test",
        "LOGS_ENDPOINT": "https://example.invalid/logs",
        "LOGS_AUTHORIZATION": "test",
        "TRACES_ENDPOINT": "https://example.invalid/traces",
        "TRACES_AUTHORIZATION": "test",
        "METRICS_ENDPOINT": "https://example.invalid/metrics",
        "METRICS_AUTHORIZATION": "test",
        "SELF_METRICS_ENDPOINT": "https://example.invalid/metrics",
        "SELF_METRICS_AUTHORIZATION": "test",
        "LANGFUSE_OTEL_ENDPOINT": "https://example.invalid/langfuse",
        "LANGFUSE_AUTH_STRING": "dGVzdDp0ZXN0",
    }
    for label, block in collector_yaml_blocks(skill_root):
        parsed = yaml.safe_load(block)
        if isinstance(parsed, dict) and {"receivers", "service"} <= set(parsed):
            validate_one_collector_config(label, block, environment)
            continue
        wrapped = fragment_as_config(parsed)
        if wrapped is None:
            # Nothing the binary can check: a Compose file, or a pipelines-only
            # snippet naming components from another fence. Reported, never
            # silent, so partial coverage stays visible.
            print(f"NOTE: {label} is not an image-validatable config; syntax only")
            continue
        validate_one_collector_config(
            f"{label} (wrapped fragment)",
            yaml.safe_dump(wrapped, sort_keys=False),
            environment,
        )


def validate_one_collector_config(
    label: str, config_text: str, environment: dict[str, str]
) -> None:
    with tempfile.TemporaryDirectory(prefix="observability-skill-") as temp_dir:
        config_path = Path(temp_dir) / "config.yaml"
        config_path.write_text(config_text, encoding="utf-8")
        command = [
            "docker",
            "run",
            "--rm",
            "--volume",
            f"{config_path}:/etc/otelcol/config.yaml:ro",
        ]
        for key, value in environment.items():
            command.extend(["--env", f"{key}={value}"])
        command.extend(
            [COLLECTOR_IMAGE, "validate", "--config=/etc/otelcol/config.yaml"]
        )
        result = subprocess.run(
            command, check=False, capture_output=True, text=True
        )
        combined_output = result.stdout + result.stderr
        require(
            result.returncode == 0,
            f"Collector image validation failed for {label}:\n"
            + combined_output,
        )
        require(
            "legacy service.telemetry.resource inline map format"
            not in combined_output.lower(),
            f"Collector image reported deprecated self-telemetry resource schema "
            f"for {label}:\n{combined_output}",
        )


def validate_genai_attribute_inventory(skill_root: Path) -> None:
    """No invented key inside the standard `gen_ai.*` namespace.

    Attributes are the larger and higher-risk surface; checking only metric
    names left rule 3 as an assertion. Double-quoted literals are code; prose
    uses backticks, so counter-examples in naming.md do not trip this.
    """
    known = STANDARD_GENAI_ATTRIBUTES | STANDARD_GENAI_EVENTS | STANDARD_GENAI_METRICS
    offenders: dict[str, set[str]] = {}
    for document in skill_root.rglob("*.md"):
        text = document.read_text(encoding="utf-8")
        for literal in re.findall(r'"(gen_ai\.[a-z0-9_.]+)"', text):
            if literal not in known:
                offenders.setdefault(
                    str(document.relative_to(skill_root)), set()
                ).add(literal)
    require(
        not offenders,
        "gen_ai.* keys not in the pinned inventory (invent under app.gen_ai.* "
        "instead, or add the row deliberately after checking the pinned "
        "convention revision):\n"
        + "\n".join(
            f"  {path}: {sorted(keys)}" for path, keys in sorted(offenders.items())
        ),
    )


def validate_compatibility(skill_root: Path) -> list[str]:
    notes: list[str] = []
    text = (skill_root / "references/compatibility.md").read_text(encoding="utf-8")
    review_by = re.search(r"Review by: \*\*(\d{4}-\d{2}-\d{2})\*\*", text)
    require(review_by is not None, "compatibility contract has no `Review by:` date")
    if date.today().isoformat() > review_by.group(1):
        # A warning, not a failure: a stale contract is a prompt to re-check
        # the pinned versions, not a broken package.
        notes.append(
            f"compatibility contract is past its review-by date "
            f"({review_by.group(1)}); every version-sensitive example is unverified"
        )
    for required in (
        "2026-09-02",
        "1.44",
        "1.44.0",
        "eaefa142a94cefe5d199d47e4a73727dfbd825df",
        "1.3.18",
        "1.6.1",
        "langchain-aws 1.7.4",
        "stopReason",
        "1.2.11",
        "0.159.0",
        "opentelemetry-instrumentation-aws-lambda",
        "0.65b0",
        "messaging.operation.name",
        'x-langfuse-ingestion-version: "4"',
    ):
        require(required in text, f"compatibility contract missing {required}")
    return notes


def validate_resource_identity_contract(skill_root: Path) -> None:
    identity_path = skill_root / "references/setup/resource_identity.md"
    identity = identity_path.read_text(encoding="utf-8")
    require_phrases(
        identity,
        (
            "service.namespace",
            "service.name",
            "service.instance.id",
            "deployment.environment.name",
            "service.version",
            "full Git commit SHA",
        ),
        context="resource identity contract",
    )
    # The shape of a repository mapping, not one repository's literal values.
    # Concrete namespaces belong in references/local/, routed on a match: a
    # namespace sitting in an always-loaded file gets adopted by unrelated
    # services, and pinning the literals here made the skill ungeneralisable.
    require(
        "service.namespace = <" in identity and "service.name      = <" in identity,
        "resource identity core must show a placeholder mapping, not a concrete one",
    )
    for local_only in ("product-data-management-automation", "pdma-api", "pdma-worker"):
        require(
            local_only not in identity,
            f"repository-specific value {local_only} leaked into the shared "
            "identity reference; move it to references/local/",
        )
    local_dir = skill_root / "references/local"
    require(local_dir.is_dir(), "references/local/ is missing")
    for local_file in local_dir.glob("*.md"):
        text = local_file.read_text(encoding="utf-8")
        require(
            "Do not open this file unless" in text,
            f"{local_file.name} lacks a conditional-load guard",
        )
    require(
        "deployment.environment.name` is **not** part" in identity,
        "environment is not excluded from service-instance uniqueness",
    )
    require(
        "gateway Collector must not derive `service.instance.id`" in identity,
        "gateway Collector ownership guard is missing",
    )
    for forbidden in ("## Kubernetes", "## Docker Compose", "## Amazon ECS"):
        require(forbidden not in identity, f"runtime detail remains in identity core: {forbidden}")

    kubernetes = (
        skill_root / "references/setup/resource_kubernetes.md"
    ).read_text(encoding="utf-8")
    for required in ("metadata.uid", "k8s.pod.uid", "SERVICE_INSTANCE_ID"):
        require(required in kubernetes, f"Kubernetes identity missing {required}")

    compose = (
        skill_root / "references/setup/resource_docker_compose.md"
    ).read_text(encoding="utf-8")
    for required in (
        "container.id",
        "short",
        "Do not also set `container.id=$HOSTNAME`",
        "Compose expands",
        "host environment",
    ):
        require(required in compose, f"Docker Compose identity missing {required}")

    ecs = (skill_root / "references/setup/resource_ecs.md").read_text(
        encoding="utf-8"
    )
    for required in (
        "ECS_CONTAINER_METADATA_URI_V4",
        "TaskARN",
        "ContainerARN",
        "DockerId",
        "ecs_resource_attributes",
        "instance_scope",
        "CONTAINER_V4",
        "TASK_V4",
        "/taskWithTags",
    ):
        require(required in ecs, f"ECS identity missing {required}")
    require(
        'instance_scope: Literal["task", "container"]' in ecs,
        "ECS resolver does not make instance granularity explicit",
    )

    processes = (
        skill_root / "references/setup/resource_processes.md"
    ).read_text(encoding="utf-8")
    for required in ("UUID v4", "UUID v5", "after the fork"):
        require(required in processes, f"process identity missing {required}")

    package_layout = (
        skill_root / "references/setup/package_layout.md"
    ).read_text(encoding="utf-8")
    for required in (
        'alias="SERVICE_NAMESPACE"',
        'alias="SERVICE_INSTANCE_ID"',
        "default_factory=lambda: str(uuid4())",
        "full Git commit SHA",
    ):
        require(required in package_layout, f"package settings missing {required}")
    require(
        'alias="HOSTNAME"' not in package_layout,
        "HOSTNAME still owns service.instance.id in generic settings",
    )

    bootstrap = (
        skill_root / "references/setup/sdk_bootstrap.md"
    ).read_text(encoding="utf-8")
    require(
        '"service.namespace": settings.service_namespace' in bootstrap,
        "SDK resource omits service.namespace",
    )
    require(
        '"service.instance.id": settings.service_instance_id' in bootstrap,
        "SDK resource omits resolved service.instance.id",
    )
    require(
        "pod name in Kubernetes" not in bootstrap,
        "SDK bootstrap still recommends pod name as instance identity",
    )

    verification = (skill_root / "references/verification.md").read_text(
        encoding="utf-8"
    )
    for required in (
        "Start two replicas",
        "full Git commit SHA supplied by CI/build",
        "A gateway Collector does not stamp application telemetry",
        "resourcedetection` uses `override: false`",
    ):
        require(required in verification, f"identity verification missing {required}")


def validate_ecs_resolver_fixtures(skill_root: Path) -> None:
    document = skill_root / "references/setup/resource_ecs.md"
    blocks = complete_python_blocks(document)
    require(len(blocks) == 1, "expected one complete ECS resolver template")
    namespace: dict[str, object] = {}
    exec(compile(blocks[0], str(document), "exec"), namespace)

    task_arn = (
        "arn:aws:ecs:eu-west-1:111122223333:task/"
        "pricing/158d1c8083dd49d6b527399fd6414f5c"
    )
    container_arn = (
        "arn:aws:ecs:eu-west-1:111122223333:container/cluster/abc123"
    )
    docker_id = "ee08638adaaf009d78c248913f629e382"
    task = {
        "Cluster": "arn:aws:ecs:eu-west-1:111122223333:cluster/pricing",
        "TaskARN": task_arn,
    }
    container = {"ContainerARN": container_arn, "DockerId": docker_id}

    def fake_read(url: str) -> dict[str, str]:
        return task if url.endswith("/task") else container

    namespace["_read_metadata"] = fake_read
    resolve = namespace["ecs_resource_attributes"]
    task_attributes = resolve("http://169.254.170.2/v4/mock", instance_scope="task")
    require(
        task_attributes["service.instance.id"] == task_arn,
        "ECS task scope does not select TaskARN",
    )
    container_attributes = resolve(
        "http://169.254.170.2/v4/mock", instance_scope="container"
    )
    require(
        container_attributes["service.instance.id"] == container_arn,
        "ECS container scope does not select ContainerARN",
    )

    container.pop("ContainerARN")
    fallback_attributes = resolve(
        "http://169.254.170.2/v4/mock", instance_scope="container"
    )
    require(
        fallback_attributes["service.instance.id"] == docker_id,
        "ECS container scope does not fall back to DockerId",
    )
    try:
        resolve("http://169.254.170.2/v4/mock", instance_scope="invalid")
    except ValueError:
        pass
    else:
        raise ValidationError("ECS resolver accepts an invalid instance scope")


def validate_async_work_contract(skill_root: Path) -> None:
    router = " ".join(
        (skill_root / "SKILL.md").read_text(encoding="utf-8").split()
    )
    require_phrases(
        router,
        (
            "DB-backed state machines",
            "Durable handoffs carry context",
            "stable workflow/run ID",
        ),
        context="durable-work router",
    )

    discovery = " ".join(
        (skill_root / "references/discovery.md")
        .read_text(encoding="utf-8")
        .split()
    )
    for required in (
        "FOR UPDATE SKIP LOCKED",
        "otel_traceparent",
        "carrier atomically with the work item/state change",
        "workflow_run_id",
    ):
        require(required in discovery, f"durable-work discovery missing {required}")

    handoffs = " ".join(
        (skill_root / "references/tracing/async_handoffs.md")
        .read_text(encoding="utf-8")
        .split()
    )
    for required in (
        "Decide parent-or-link first",
        "traceparent",
        "context=otel_context.Context()",
        "context=None",
        "does not extend the already-ended producer root span",
        "late spans",
        "untrusted metadata",
    ):
        require(required in handoffs, f"async-handoff contract missing {required}")

    durable = " ".join(
        (skill_root / "references/tracing/durable_work.md")
        .read_text(encoding="utf-8")
        .split()
    )
    for required in (
        "DB-Backed Work Queues and Durable State Machines",
        "normalize_trace_carrier",
        "context=otel_context.Context()",
        "links=links",
        "app.workflow.run.id",
        "workflow_run_id",
        "same database transaction",
        "Retrying the **same** work item keeps its original scheduling carrier",
    ):
        require(required in durable, f"durable-work tracing missing {required}")

    queue_raw = (skill_root / "references/tracing/queue_messaging.md").read_text(
        encoding="utf-8"
    )
    queue = " ".join(queue_raw.split())
    for required in (
        "Boto3SQSGetter",
        "Boto3SQSSetter",
        "MessageAttributeNames",
        "context=otel_context.Context()",
        "messaging.operation.name",
        "messaging.batch.message_count",
        "legacy 1.11 telemetry schema",
        "use_span_links=False",
        "use_span_links=True",
        "OTEL_PYTHON_DISABLED_INSTRUMENTATIONS=boto3",
    ):
        require(required in queue, f"queue tracing missing {required}")
    require(
        queue_raw.count('"messaging.operation.name"') >= 4,
        "every manual SQS producer/consumer template must set messaging.operation.name",
    )
    require(
        '"publish sqs' not in queue_raw and '"consume sqs' not in queue_raw,
        "queue templates retain pre-1.44 messaging span names",
    )

    lambda_reference = (
        skill_root / "references/tracing/lambda_functions.md"
    ).read_text(encoding="utf-8")
    require(
        lambda_reference.count("AWS_LAMBDA_LOG_STREAM_NAME") >= 2
        and "full `AWS_LAMBDA_LOG_STREAM_NAME`" in lambda_reference,
        "Lambda execution-environment identity ignores the prescribed log stream",
    )
    require(
        "cloud.platform = aws_lambda" in lambda_reference,
        "Lambda resource identity omits cloud.platform",
    )

    scheduled = " ".join(
        (skill_root / "references/tracing/scheduled_jobs.md")
        .read_text(encoding="utf-8")
        .split()
    )
    for required in ("Always start a new root trace", "shutdown_observability()"):
        require(required in scheduled, f"scheduled-job tracing missing {required}")
    for forbidden in ("Boto3SQSGetter", "FOR UPDATE SKIP LOCKED", "MessageAttributes"):
        require(forbidden not in scheduled, f"scheduled-job reference leaks {forbidden}")

    worker_runtime = " ".join(
        (skill_root / "references/tracing/worker_runtime.md")
        .read_text(encoding="utf-8")
        .split()
    )
    for required in (
        "signal.SIGTERM",
        "asyncio.create_task()",
        "asyncio.to_thread()",
        "ThreadPoolExecutor.submit()",
        "loop.run_in_executor()",
        "context.attach",
        "context.detach",
    ):
        require(required in worker_runtime, f"worker runtime missing {required}")

    logging = " ".join(
        (skill_root / "references/logging/structlog.md")
        .read_text(encoding="utf-8")
        .split()
    )
    for required in (
        "Logs carry **execution correlation**; traces carry **causal topology**",
        "worker logs use trace_id B",
        "workflow_run_id",
        "causal_trace_id",
    ):
        require(required in logging, f"durable-work logging missing {required}")

    verification = " ".join(
        (skill_root / "references/verification.md")
        .read_text(encoding="utf-8")
        .split()
    )
    for required in (
        "durable DB work",
        "carrier and the work item/runnable state commit atomically",
        "logs carry the current worker",
    ):
        require(required in verification, f"durable-work verification missing {required}")


def validate_lambda_contract(skill_root: Path) -> None:
    lambda_path = skill_root / "references/tracing/lambda_functions.md"
    text = lambda_path.read_text(encoding="utf-8")
    for required in (
        "AWS_LAMBDA_EXEC_WRAPPER=/opt/otel-handler",
        "/opt/otel-instrument",
        "OTEL_PROPAGATORS=tracecontext,xray-lambda",
        "**not** use `xray-lambda`",
        "faas.invocation_id",
        "aws.lambda.invoked_arn",
        "OTEL_INSTRUMENTATION_AWS_LAMBDA_FLUSH_TIMEOUT",
        "force_flush()",
        "Do not use `context.aws_request_id` as `service.instance.id`",
        "API_GATEWAY_EVENT",
        "SQS_EVENT",
        "LAMBDA_CONTEXT",
        "partial-batch failure",
    ):
        require(required in text, f"Lambda contract missing {required}")
    require(
        not re.search(r"arn:aws:lambda:[^\s]+:layer:", text),
        "Lambda reference hardcodes a regional/versioned layer ARN",
    )


def validate_production_policy_contract(skill_root: Path) -> None:
    router = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    require(
        "references/tracing/production_policy.md" in router,
        "production policy is not routed from SKILL.md",
    )
    require(
        "Don't accept a force-sampling signal from an untrusted" in router,
        "force-sampling trust guard is missing from SKILL.md",
    )

    policy = (
        skill_root / "references/tracing/production_policy.md"
    ).read_text(encoding="utf-8")
    for required in (
        "new-release burn-in",
        "actual effective retained ratio",
        "minimum active trace capacity",
        "estimate_trace_budget.py",
        "authenticated internal control",
        "`tracecontext` by default",
        "tested rollback path",
    ):
        require(required in policy, f"production policy missing {required}")

    discovery = (skill_root / "references/discovery.md").read_text(
        encoding="utf-8"
    )
    for required in (
        "p99 complete-trace arrival time",
        "backend ingest/retention budget",
        "Do not silently substitute `5%`",
    ):
        require(required in discovery, f"production discovery missing {required}")

    production = (skill_root / "references/collector/production.md").read_text(
        encoding="utf-8"
    )
    for required in (
        "filter/successful_probes",
        "decision_cache:",
        "num_traces >= new_traces_per_second",
        "keep-release-burn-in",
    ):
        require(required in production, f"production Collector guide missing {required}")

    package_layout = (
        skill_root / "references/setup/package_layout.md"
    ).read_text(encoding="utf-8")
    bootstrap = (skill_root / "references/setup/sdk_bootstrap.md").read_text(
        encoding="utf-8"
    )
    require(
        "| `OTEL_PROPAGATORS` |" in package_layout
        and "| `tracecontext` |" in package_layout,
        "package layout does not default propagators to tracecontext",
    )
    require(
        "export OTEL_PROPAGATORS=tracecontext" in bootstrap,
        "SDK bootstrap does not default propagators to tracecontext",
    )


def validate_routing_contract(skill_root: Path) -> None:
    router_path = skill_root / "SKILL.md"
    router_text = router_path.read_text(encoding="utf-8")
    router = " ".join(router_text.split())
    discovery = " ".join(
        (skill_root / "references/discovery.md")
        .read_text(encoding="utf-8")
        .split()
    )

    paths = (
        "references/tracing/async_handoffs.md",
        "references/tracing/queue_messaging.md",
        "references/tracing/durable_work.md",
        "references/tracing/scheduled_jobs.md",
        "references/tracing/worker_runtime.md",
        "references/tracing/lambda_functions.md",
        "references/setup/resource_kubernetes.md",
        "references/setup/resource_docker_compose.md",
        "references/setup/resource_ecs.md",
        "references/setup/resource_processes.md",
        "references/setup/startup_fastapi.md",
        "references/setup/startup_worker_cli.md",
        "references/setup/startup_prefork.md",
    )
    for path in paths:
        require(path in router, f"SKILL router does not expose {path}")

    rows = {
        line.split("|", 2)[1].strip(): line
        for line in router_text.splitlines()
        if line.startswith("|") and line.count("|") >= 3
    }

    def require_row(
        label: str,
        required: tuple[str, ...],
        forbidden: tuple[str, ...] = (),
    ) -> None:
        row = rows.get(label, "")
        require(row, f"routing row missing: {label}")
        for fragment in required:
            require(fragment in row, f"{label} route missing {fragment}")
        for fragment in forbidden:
            require(fragment not in row, f"{label} route leaks {fragment}")

    require_row(
        "Scheduled job or CLI batch",
        ("scheduled_jobs.md",),
        ("queue_messaging.md", "durable_work.md", "async_handoffs.md"),
    )
    require_row(
        "Queue publish or direct queue consumer",
        ("async_handoffs.md", "queue_messaging.md"),
        ("durable_work.md", "scheduled_jobs.md"),
    )
    require_row(
        "DB-backed queue, outbox, lease, or durable state transition",
        ("async_handoffs.md", "durable_work.md"),
        ("queue_messaging.md", "scheduled_jobs.md"),
    )
    require_row("Amazon ECS or Fargate", ("resource_ecs.md",))
    require_row("AWS Lambda function", ("lambda_functions.md",))
    require_row("FastAPI", ("sdk_bootstrap.md", "startup_fastapi.md"))
    require_row(
        "Gunicorn/uWSGI or another pre-fork server",
        ("sdk_bootstrap.md", "startup_prefork.md", "resource_processes.md"),
    )

    for required in (
        "managed invocation",
        "tracing/lambda_functions.md",
        "tracing/scheduled_jobs.md",
        "tracing/durable_work.md",
    ):
        require(required in discovery, f"discovery routing missing {required}")

    stale_path = skill_root / "references/tracing/workers_and_queues.md"
    require(not stale_path.exists(), "stale workers_and_queues.md still exists")
    for document in skill_root.rglob("*.md"):
        require(
            "workers_and_queues.md" not in document.read_text(encoding="utf-8"),
            f"stale workers_and_queues.md route in {document.relative_to(skill_root)}",
        )


# Per-file caps. Anything not listed falls back to DEFAULT_LINE_CAP, so a new
# reference cannot grow unbounded just by not being in the table.
DEFAULT_LINE_CAP = 400
LINE_CAPS = {
    "SKILL.md": 300,
    "references/discovery.md": 320,
    "references/troubleshooting.md": 160,
    "references/testing.md": 260,
    "references/verification.md": 340,
    "references/compatibility.md": 90,
    "references/conventions/naming.md": 220,
    "references/conventions/errors.md": 240,
    "references/setup/resource_identity.md": 220,
    "references/setup/sdk_bootstrap.md": 380,
    "references/setup/resource_ecs.md": 230,
    "references/setup/package_layout.md": 240,
    "references/setup/shared_library.md": 240,
    "references/setup/auto_instrumentation.md": 200,
    "references/tracing/async_handoffs.md": 90,
    "references/tracing/queue_messaging.md": 300,
    "references/tracing/durable_work.md": 230,
    "references/tracing/scheduled_jobs.md": 80,
    "references/tracing/worker_runtime.md": 110,
    "references/tracing/lambda_functions.md": 300,
    "references/tracing/production_policy.md": 240,
    "references/tracing/genai/retrieval.md": 140,
    "references/tracing/genai/content_capture.md": 440,
    "references/tracing/genai/langchain/model_callback.md": 550,
    "references/collector/production.md": 610,
    "references/metrics/genai.md": 400,
    "references/logging/structlog.md": 420,
}
# The set loaded on every invocation, whatever the task. This is the number
# that actually governs per-invocation cost, so it is capped as a whole.
UNCONDITIONAL_SET = (
    "SKILL.md",
    "references/conventions/naming.md",
    "references/conventions/errors.md",
    "references/verification.md",
)
UNCONDITIONAL_LINE_CAP = 1_100


def validate_context_footprint(skill_root: Path) -> list[str]:
    notes: list[str] = []
    for document in sorted(skill_root.rglob("*.md")):
        relative = str(document.relative_to(skill_root))
        maximum = LINE_CAPS.get(relative, DEFAULT_LINE_CAP)
        line_count = len(document.read_text(encoding="utf-8").splitlines())
        require(
            line_count <= maximum,
            f"context budget exceeded for {relative}: {line_count} > {maximum}",
        )

    total = sum(
        len((skill_root / relative).read_text(encoding="utf-8").splitlines())
        for relative in UNCONDITIONAL_SET
    )
    require(
        total <= UNCONDITIONAL_LINE_CAP,
        f"unconditional load is {total} lines > {UNCONDITIONAL_LINE_CAP}; "
        "move material into a conditionally routed file",
    )
    notes.append(
        f"unconditional load: {total}/{UNCONDITIONAL_LINE_CAP} lines "
        f"({UNCONDITIONAL_LINE_CAP - total} spare)"
    )
    return notes


def validate_review_regressions(skill_root: Path) -> None:
    model = (
        skill_root
        / "references/tracing/genai/langchain/model_callback.md"
    ).read_text(encoding="utf-8")
    require(
        'for key in ("ls_model_name", "ls_model_type")' not in model,
        "ls_model_type is still a model-name fallback",
    )
    require(
        'span_name = f"chat {model}" if model else "chat"' in model
        and "unknown_model" not in model,
        "missing LangChain model identity is represented by an invented sentinel",
    )
    require(
        '"chunk_count": 0' in model and '"captured_chunks"' in model,
        "streaming count and content buffer are not independent",
    )
    for source_label, otel_value in (
        ("azure", "azure.ai.openai"),
        ("amazon_bedrock", "aws.bedrock"),
        ("mistral", "mistral_ai"),
        ("xai", "x_ai"),
    ):
        require(
            f'"{source_label}": "{otel_value}"' in model,
            f"LangChain provider alias {source_label} is not normalized to {otel_value}",
        )

    logging = (
        skill_root / "references/logging/structlog.md"
    ).read_text(encoding="utf-8")
    require(
        logging.index("add_exception_fields,")
        < logging.index("structlog.processors.format_exc_info,"),
        "exception fields are extracted after format_exc_info consumes exc_info",
    )
    for required in (
        '"exception.type"',
        '"exception.message"',
        'event_name == "gen_ai.client.operation.exception"',
        "SeverityNumber.WARN",
        "inject_trace_context=True",
        "otelTraceID",
        "OTEL_PYTHON_LOG_AUTO_INSTRUMENTATION=false",
    ):
        require(required in logging, f"named exception event contract missing {required}")

    streaming = (
        skill_root
        / "references/tracing/genai/langchain/streaming_and_agent_span.md"
    ).read_text(encoding="utf-8")
    require('version="v2"' in streaming, "LangChain stream schema is not explicit")
    # Every wrapper must report fan-out. The non-streaming one scopes counters
    # with the context manager; the streaming ones cannot, because that scope
    # would span a `yield` — they bind per resumption instead. Both shapes are
    # accepted; omitting the counters entirely is not.
    require(
        streaming.count("invocation_counters() as counters")
        + streaming.count("agent_step(span, counters)")
        >= 3,
        "one or more agent wrappers omit invocation counters",
    )
    require(
        streaming.count("record_agent_result(") >= 4,
        "an agent wrapper does not record the fan-out metrics",
    )
    # The generator context-leak fix, in both files that stream. A span held
    # current across a `yield` leaks into the consumer; both files must use
    # start_span + explicit end() after their streaming heading.
    provider = (
        skill_root / "references/tracing/genai/provider_sdk.md"
    ).read_text(encoding="utf-8")
    require(
        "Why the span is never current across a `yield`" in provider,
        "provider_sdk.md no longer explains the generator context rule",
    )
    require(
        'finish_reason or ("error" if error_type else "unknown")' in provider,
        "streaming provider output can omit its required finish reason",
    )
    for label, text, heading in (
        ("provider_sdk.md", provider, "## Streaming"),
        ("streaming_and_agent_span.md", streaming, "### Token streaming"),
    ):
        # Prose may name the API; a code fence in a yielding wrapper may not.
        require(
            "with tracer.start_as_current_span(" not in text.split(heading, 1)[-1],
            f"{label} holds start_as_current_span across a yield again",
        )
    require(
        "agent_step(span, counters)" in streaming,
        "streaming agent wrappers do not bracket each resumption",
    )

    tools = (
        skill_root
        / "references/tracing/genai/langchain/tools_and_middleware.md"
    ).read_text(encoding="utf-8")
    require(
        'GENAI_TOOL_CALL_ID: request.tool_call.get("id", "")' not in tools
        and 'if tool_call_id := request.tool_call.get("id"):' in tools,
        "optional tool-call ID is emitted as an empty string",
    )

    content = (
        skill_root / "references/tracing/genai/content_capture.md"
    ).read_text(encoding="utf-8")
    require(
        '"finish_reason": str(finish_reason or "unknown")' in content
        and 'value.get("id", "")' not in content
        and 'getattr(call, "id", "")' not in content,
        "content serializer violates required finish-reason or optional-ID schema",
    )
    require_phrases(
        content,
        (
            "app.gen_ai.observation.input",
            "app.gen_ai.observation.output",
            "langfuse.observation.input",
            "langfuse.observation.output",
            "portable OpenTelemetry source of truth",
        ),
        context="backend presentation projection contract",
    )
    token_usage = (
        skill_root / "references/tracing/genai/token_usage.md"
    ).read_text(encoding="utf-8")
    require(
        "usage is simply zero everywhere" not in token_usage
        and "usage attributes and observations are simply absent" in token_usage,
        "missing streaming usage is described as zero instead of absent",
    )
    all_markdown = "\n".join(
        document.read_text(encoding="utf-8") for document in skill_root.rglob("*.md")
    )
    require(
        "Token counts zero on streamed calls only" not in all_markdown
        and "token counts are zero on streamed calls only" not in all_markdown,
        "missing streamed usage is still documented as explicit zero",
    )

    for relative in (
        "references/collector/component.md",
        "references/collector/production.md",
    ):
        text = (skill_root / relative).read_text(encoding="utf-8")
        require(
            'x-langfuse-ingestion-version: "4"' in text,
            f"{relative} lacks the Langfuse v4 header",
        )

    collector = (skill_root / "references/collector/component.md").read_text(
        encoding="utf-8"
    )
    require_phrases(
        collector,
        (
            "attributes/langfuse_observation_io",
            "from_attribute: app.gen_ai.observation.input",
            "from_attribute: app.gen_ai.observation.output",
            "action: delete",
        ),
        context="Langfuse Collector presentation mapping",
    )

    for relative in (
        "references/tracing/genai/langchain/model_callback.md",
        "references/tracing/genai/provider_sdk.md",
        "references/setup/sdk_bootstrap.md",
        "references/setup/resource_ecs.md",
        "references/collector/production.md",
        "references/tracing/genai/content_capture.md",
        "references/tracing/queue_messaging.md",
        "references/tracing/durable_work.md",
        "references/tracing/lambda_functions.md",
    ):
        require(
            "## Contents" in (skill_root / relative).read_text(encoding="utf-8"),
            f"{relative} lacks navigation",
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "skill_root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--quick-validator", type=Path)
    parser.add_argument(
        "--official-validator",
        action="store_true",
        help=(
            "fail if Codex's skill-creator quick_validate.py is not installed; "
            "by default its absence is a warning so every other check still runs"
        ),
    )
    parser.add_argument(
        "--collector-image",
        action="store_true",
        help=f"also validate every Collector YAML block with {COLLECTOR_IMAGE}",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skill_root = args.skill_root.resolve()
    notes: list[str] = []
    try:
        notes += run_official_validator(
            skill_root,
            find_quick_validator(args.quick_validator),
            required=args.official_validator,
        )
        validate_references(skill_root)
        validate_standard_genai_contract(skill_root)
        validate_genai_attribute_inventory(skill_root)
        validate_python(skill_root)
        validate_trace_budget_calculator(skill_root)
        validate_serializer_fixtures(skill_root)
        validate_otlp_first_contract(skill_root)
        validate_collector_yaml(skill_root)
        validate_measured_values_are_marked(skill_root)
        notes += validate_compatibility(skill_root)
        validate_resource_identity_contract(skill_root)
        validate_ecs_resolver_fixtures(skill_root)
        validate_async_work_contract(skill_root)
        validate_lambda_contract(skill_root)
        validate_production_policy_contract(skill_root)
        validate_routing_contract(skill_root)
        notes += validate_context_footprint(skill_root)
        validate_review_regressions(skill_root)
        if args.collector_image:
            validate_collector_image(skill_root)
    except ValidationError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("PASS: observability skill validation")
    for note in notes:
        print(f"NOTE: {note}")
    if not args.collector_image:
        print(f"NOTE: rerun with --collector-image to validate {COLLECTOR_IMAGE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
