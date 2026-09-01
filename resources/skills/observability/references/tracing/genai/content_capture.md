# Content Capture

Prompts, system instructions, tool definitions, tool arguments, tool results, retrieved documents, and model outputs can all contain user data. They are **opt-in**, everywhere, on every code path in this skill.

Read `attributes.md` first for the constants module this imports from.

## Contents

- [Capture switch](#one-switch)
- [Complete serializers](#the-serializers)
- [Partial and truncated capture](#mark-a-partial-capture)
- [Backend policy](#where-content-is-allowed-to-go)
- [Verification](#verify)

---

## One switch

**`CAPTURE_AI_CONTENT`**, read from the service config object (`../../setup/package_layout.md`), never from `os.environ` at a call site.

```python
from core.config import get_settings

settings = get_settings()

if settings.capture_ai_content:
    span.set_attribute(GENAI_INPUT_MESSAGES, serialize_messages(messages))
    span.set_attribute(
        GENAI_OUTPUT_MESSAGES,
        serialize_text_output(answer, finish_reason),
    )
```

The attributes it gates:

```
gen_ai.system_instructions      gen_ai.tool.definitions
gen_ai.input.messages           gen_ai.tool.call.arguments
gen_ai.output.messages          gen_ai.tool.call.result
```

Plus retrieval query text and document contents (`provider_sdk.md`).

When capture is **off**, everything else is still recorded: model, provider, operation, parameters, latency, TTFC, token usage, finish reasons, errors. An observability implementation with content capture disabled is still fully useful for operations — it just cannot show you what was said.

Gate the *collection*, not only the *write*. A streaming callback that accumulates every token into a list and then skips `set_attribute` still buffers every response in memory for nothing (`langchain/model_callback.md`).

---

## The serializers

`gen_ai.input.messages` and `gen_ai.output.messages` are message arrays of `{role, parts}`, serialized to JSON because the attribute type must be scalar. This is a **complete framework-tolerant template**, not a standalone sketch. It handles dict messages, LangChain messages, normalized multimodal content blocks, tool calls, batched LangChain chat-model input, and multiple output choices.

<!-- complete-python-template -->
```python
# observability/genai_content.py
import json
from typing import Any


ROLE_BY_MESSAGE_TYPE = {
    "human": "user",
    "ai": "assistant",
    "system": "system",
    "tool": "tool",
    "function": "tool",
}


def _role(message: Any, default: str = "user") -> str:
    if isinstance(message, dict):
        value = message.get("role") or message.get("type")
    else:
        value = getattr(message, "role", None) or getattr(message, "type", None)
    return ROLE_BY_MESSAGE_TYPE.get(str(value), str(value or default))


def _part(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        return {"type": "text", "content": value}
    if not isinstance(value, dict):
        return {"type": "text", "content": str(value)}

    part_type = str(value.get("type") or "text")
    if part_type in {"text", "reasoning"}:
        return {
            "type": part_type,
            "content": value.get("content", value.get("text", "")),
        }
    if part_type in {"tool_call", "tool_use"}:
        name = value.get("name")
        if not name:
            # A standard tool_call requires a name. Keep malformed provider
            # data as an extensible generic part instead of inventing identity.
            return {
                "type": "unknown_tool_call",
                "arguments": value.get("arguments", value.get("args", {})),
            }
        result = {
            "type": "tool_call",
            "name": str(name),
            "arguments": value.get("arguments", value.get("args", {})),
        }
        if call_id := value.get("id"):
            result["id"] = str(call_id)
        return result

    # Preserve normalized multimodal blocks when available. Content capture is
    # already opt-in; default=str below prevents SDK-specific objects raising.
    return dict(value)


def _parts(message: Any) -> list[dict[str, Any]]:
    if isinstance(message, dict):
        content = message.get("content", "")
        tool_calls = message.get("tool_calls") or []
    else:
        content = getattr(message, "content_blocks", None)
        if content is None:
            content = getattr(message, "content", "")
        tool_calls = getattr(message, "tool_calls", None) or []

    values = content if isinstance(content, list) else [content]
    result = [_part(value) for value in values]
    if not any(part.get("type") == "tool_call" for part in result):
        for call in tool_calls:
            if isinstance(call, dict):
                result.append(_part({"type": "tool_call", **call}))
            else:
                result.append(
                    _part(
                        {
                            "type": "tool_call",
                            "id": getattr(call, "id", None),
                            "name": getattr(call, "name", None),
                            "args": getattr(call, "args", {}),
                        }
                    )
                )
    return result


def _message(message: Any, default_role: str = "user") -> dict[str, Any]:
    role = _role(message, default_role)
    if role == "tool":
        if isinstance(message, dict):
            response = message.get("content", "")
            tool_call_id = message.get("tool_call_id")
        else:
            response = getattr(message, "content", "")
            tool_call_id = getattr(message, "tool_call_id", None)
        part: dict[str, Any] = {
            "type": "tool_call_response",
            "response": response,
        }
        if tool_call_id:
            part["id"] = str(tool_call_id)
        return {"role": role, "parts": [part]}
    return {"role": role, "parts": _parts(message)}


def serialize_messages(messages: list[Any]) -> str:
    """Request messages -> the standard {role, parts} array."""
    return json.dumps([_message(message) for message in messages], default=str)


def serialize_chat_model_input(
    messages: list[Any] | list[list[Any]],
) -> tuple[str, int]:
    """LangChain callback input, returning JSON and physical batch size.

    The standard attribute describes one conversation. When LangChain batches
    several conversations into one physical request, capture the first and let
    the caller mark the telemetry as truncated instead of inventing a nested
    schema under the standard attribute.
    """
    if not messages:
        return "[]", 0
    if isinstance(messages[0], (list, tuple)):
        batches = messages
    else:
        batches = [messages]
    return serialize_messages(list(batches[0])), len(batches)


def serialize_text_output(text: str, finish_reason: str | None) -> str:
    """A completed assistant response, streamed or not."""
    message: dict[str, Any] = {
        "role": "assistant",
        "parts": [{"type": "text", "content": text}],
        # Required by the pinned output-message schema. `unknown` is used only
        # when a framework omitted the provider's reason.
        "finish_reason": str(finish_reason or "unknown"),
    }
    return json.dumps([message])


def serialize_llm_result(response: Any) -> str:
    """LangChain LLMResult -> one assistant message per generation/choice."""
    output_messages: list[dict[str, Any]] = []
    for generation_list in getattr(response, "generations", None) or []:
        for generation in generation_list:
            source = getattr(generation, "message", None)
            if source is None:
                source = {"role": "assistant", "content": getattr(generation, "text", "")}
            message = _message(source, default_role="assistant")

            response_metadata = getattr(source, "response_metadata", None) or {}
            generation_info = getattr(generation, "generation_info", None) or {}
            finish_reason = (
                response_metadata.get("finish_reason")
                or generation_info.get("finish_reason")
            )
            message["finish_reason"] = str(finish_reason or "unknown")
            output_messages.append(message)
    return json.dumps(output_messages, default=str)


def serialize_tool_input(args: Any) -> str:
    return json.dumps(args, default=str)


def serialize_tool_output(result: Any) -> str:
    return json.dumps(result, default=str) if not isinstance(result, str) else result
```

`default=str` on the tool serializers is deliberate: a tool returning a dataclass, a `Decimal`, or a `datetime` must not make `json.dumps` raise inside a span.

Every output choice carries `finish_reason`, as required by the pinned JSON schema. Preserve the provider value; `unknown` is only a fail-soft fallback when a framework omits it. Optional tool-call IDs are omitted when unavailable, and a malformed nameless tool call is retained as a generic `unknown_tool_call` part rather than assigned a fabricated standard identity.

For batched LangChain input, record `app.gen_ai.input.batch_size` from the returned integer. If it is greater than one, set `app.gen_ai.input.capture_mode="truncated"`; the standard attribute intentionally contains only the first conversation rather than merging independent inputs.

`gen_ai.input.messages` is scoped to **one** model call — the history actually sent on that call. A stateless agent loop therefore repeats earlier turns on later inference spans. That is correct and faithful, not duplication to be optimised away.

### Mark a partial capture

If you deliberately record less than the full request, keep the standard array schema and say so:

```python
span.set_attribute(APP_INPUT_CAPTURE_MODE, "delta")  # none | full | delta | truncated
```

Without that marker, a filtered payload looks like a complete request, and someone will try to replay it and diagnose the wrong context. Do not invent a wrapper object inside `gen_ai.input.messages`; the standard field must remain a message array.

`gen_ai.conversation.compacted` is a different fact and must not be set here. It means the *model* received summarized or trimmed history, not that *telemetry* was truncated — see `attributes.md`.

---

## Where content is allowed to go

Capturing content in the application is one decision; which backend may store it is another. **`../../collector/component.md` owns the per-backend content policy** — read it before assuming a captured payload is allowed to leave the process.

The consequence for this file: capture being *on* does not mean every trace destination may receive the payload. If traces fan out to more than one backend, redact the payload attributes on the path to the general one — Collector work, in `../../collector/production.md` — and keep prompts out of the logs entirely (`../../logging/genai.md`).

Mask in the application first. A Collector `attributes` processor deletes by key; it cannot find a secret embedded inside an otherwise-permitted JSON string.

**Sampling is not a privacy control.** A trace not sampled today may be sampled tomorrow, and content capture must be correct either way.

---

## Verify

- With `CAPTURE_AI_CONTENT` unset or false, **no** payload attribute appears anywhere. Against a captured span dump (`../../verification.md` shows how to produce one):

```bash
grep -E 'gen_ai\.(input\.messages|output\.messages|system_instructions|tool\.definitions|tool\.call\.(arguments|result))' captured_spans.json
```

Expect no matches.

- With it enabled, the attributes appear and hold the standard message-array schema.
- Multiple generations appear as independent assistant messages, each with a finish reason; tool responses, tool calls, and multimodal parts are preserved where available.
- Batched input records its batch size and marks the first-conversation capture as truncated.
- If capture is filtered or truncated, `app.gen_ai.input.capture_mode` marks it.
- With capture off, a long streamed response allocates nothing — check the chunk buffer is empty, not just the attribute absent.
