# Mandatory GenAI root boundary

Every service that invokes an LLM, builds an agent or graph, owns prompts or AI
tools, or validates model output must create root `genai/`. This is mandatory
even for one small model call used by one application action. Never colocate GenAI
implementation in `application/`, `domain/`, `ports/`, or `adapters/`.

The rest of the application sees a technology-neutral port and typed business
result, not LangChain, LangGraph, provider SDKs, prompts, model handles, raw
provider responses, or MCP internals. Keep all AI-specific implementation below
`genai/<business-task>/`.

GenAI is not the business-execution layer. The understandable action remains in
`application/`; for example, `application/email_classification.py` owns classification
workflow and policy. `genai/email_classification/` defines and configures the AI
mechanism and may implement the `EmailClassifier` port, but it never becomes the
public business action.

These modules are not duplicates. The application action owns the business use
case; the GenAI classifier owns one remote, nondeterministic implementation of a
capability used by that use case. If a classifier contains no prompt, provider,
AI-schema, model-handle, or provider-error translation concern, it does not
belong in `genai/`. If the application module only forwards the call and contains no
use-case boundary, policy, or outcome semantics, inspect whether behavior was
misplaced or whether the action is currently thin enough to stay a single small
module.

## Application context

```text
<package>/
├── core/
│   └── context.py                  # Immutable caller/application context
└── genai/
```

`core/context.py` may carry `tenant_id`, `user_id`, authorization claims,
correlation identifiers, and allowlisted execution metadata. It is created by
the API/consumer boundary and passed into the GenAI adapter. Never let an agent
construct trusted identity or authorization context from its prompt.

LangGraph's mutable execution state is different and belongs in
`genai/<agent>/graph/state.py`.

## Standard agent shape

```text
<package>/
└── genai/
    └── pricing_agent/
        ├── llm.py                  # Model construction/binding factory
        ├── schemas.py              # Agent input/output and response schemas
        ├── prompts.py              # Prompt definitions/builders, when used
        ├── tools.py                # A few cohesive tools, when used
        ├── middleware.py           # A few custom middleware, when used
        ├── agent.py                # Agent harness factory
        └── pricer.py               # Pricer port implementation
```

This is the ordinary shape for an agent built with `create_agent`. Keep
`agent.py` setup-only. Every application-facing GenAI capability keeps
invocation, input/output translation, and port-error translation in a separate
capability-named port implementation such as `pricer.py`, `resolver.py`, or
`classifier.py`. If a GenAI component is not exposed to `application/` and is
invoked only by another GenAI capability, do not manufacture an application
port or capability adapter for it. Use generic `adapter.py` only when that is an
established repository convention.

Create `prompts.py`, `tools.py`, and `middleware.py` only when those
responsibilities exist. A LangChain agent created with `create_agent()` does not
by itself justify a project-owned `graph/` package. Add `graph/` only when the
application explicitly defines LangGraph state, nodes, routing, or edges.

## Expanded multi-agent shape

```text
<package>/
└── genai/
    ├── shared/                         # Only demonstrated multi-agent reuse
    │   ├── middleware/
    │   │   ├── tracing.py
    │   │   └── limits.py
    │   ├── prompts/
    │   │   └── safety.py
    │   ├── schemas/
    │   │   └── citations.py
    │   ├── tools/
    │   │   └── knowledge_search.py
    │   └── retrieval/
    │       ├── retriever.py
    │       ├── reranking.py
    │       └── context.py
    │
    ├── pricing_agent/                  # Standard create_agent agent
    │   ├── llm.py
    │   ├── schemas.py
    │   ├── prompts.py
    │   ├── tools/
    │   │   ├── products.py
    │   │   └── discounts.py
    │   ├── middleware.py
    │   ├── agent.py
    │   └── pricer.py
    │
    ├── resolution_agent/               # Custom graph; uses shared retrieval
    │   ├── llm.py
    │   ├── schemas.py
    │   ├── prompts.py
    │   ├── tools.py
    │   ├── agent.py
    │   ├── graph/
    │   │   ├── graph.py
    │   │   ├── state.py
    │   │   ├── nodes.py
    │   │   └── routing.py
    │   ├── checkpointer.py         # Only when graph persistence is needed
    │   └── resolver.py
    │
    └── support_agent/                  # Uses shared retrieval through a tool
        ├── llm.py
        ├── schemas.py
        ├── prompts.py
        ├── tools/
        │   └── ticket_lookup.py
        ├── middleware.py
        ├── mcp.py                      # Only when MCP tools are loaded
        ├── agent.py
        └── supporter.py
```

This expanded view illustrates variations, not required symmetry. The pricing
agent does not own a graph, the resolution agent does, and the resolution and
support agents reuse knowledge retrieval through the shared tool and retrieval
modules. Keep retrieval local to one agent until another agent actually reuses
the same tool contract, retrieval, reranking, or context semantics; promote only
the reused pieces to `genai/shared/`. `shared/` is not a staging area for code
expected to become reusable later.

## Simple structured-output capability

A small structured-output capability commonly starts with:

```text
<package>/
└── genai/
    └── email_classification/
        ├── llm.py                  # Model construction/binding factory
        ├── schemas.py              # Provider-facing structured output
        ├── prompts.py              # When owned prompts justify a module
        └── classifier.py           # EmailClassifier port implementation
```

Keep model construction in `llm.py` and typed provider-facing output in
`schemas.py`. Add `prompts.py` when the task owns non-trivial, reusable, or
versioned prompts. An application-facing capability keeps a capability-named
port implementation such as `classifier.py` for invocation, translation, and
failure mapping. Do not force unused extension modules.

## Schema ownership

Keep a Pydantic model used only as one tool's argument or result schema beside
that tool. Promote it to `schemas/tools.py` only when multiple tools reuse the
same contract. Agent-level input, output, and structured-response contracts stay
in `schemas.py` or `schemas/`; business contracts stay in `ports/` or `domain/`.
Do not create a generic `tool_schemas.py` collection by default.

## Progressive module splitting

When a module approaches 300–350 lines, review it for separable responsibilities.
Line count alone does not require converting it into a package. Convert
`tools.py`, `middleware.py`, `prompts.py`, or `schemas.py` into a same-named
package when it contains multiple cohesive responsibilities, independently
changing implementations, or distinct test concerns. A long but cohesive module
may remain a file; a shorter mixed-responsibility module may need to split
earlier. Preserve its public imports through `__init__.py` when a file-to-package
migration would otherwise cause unnecessary churn.

Do not create shared Python modules merely to represent model roles such as
primary, fast, cheap, or summarizer. When provider, model, and role differences
are configuration only, keep them in `config/`. The task-level `llm.py` factory
accepts the resolved, allowlisted construction values and applies task-specific
structured output, tools, timeouts, and other binding.

Extract `genai/shared/llm.py` only after multiple task-level modules duplicate
meaningful construction policy beyond an `init_chat_model` call and ordinary
configuration plumbing. Introduce `genai/shared/llms/` only when several real,
independently changing implementations justify a package. Provider variability
alone does not. If model/provider selection remains configurable at invocation
time, enumerate only the intended configurable fields; never expose unrestricted
provider, API-key, or base-URL overrides to untrusted callers.

## `llm.py`, optional `agent.py`, and bootstrap wiring

Every GenAI task has `llm.py`; never move model construction into the capability
implementation. It exports a construction/binding factory, not a module-global
model handle. An agent task additionally has `agent.py`, which exports a harness
factory. Never name model construction `model.py` or `models/`—those read as
domain entities.

`llm.py` accepts explicit, resolved construction values or a narrow typed
task-settings object and binds what makes the model callable—structured output,
tools, timeouts, and limits:

```python
# llm.py
from langchain.chat_models import init_chat_model

from my_service.genai.email_classification.schemas import ClassificationOutput


def build_model(*, model_name: str, model_provider: str):
    return init_chat_model(
        model=model_name,
        model_provider=model_provider,
    ).with_structured_output(ClassificationOutput)
```

`agent.py` is added when the task is an agent. Its factory accepts already
constructed models and explicit tool dependencies, then returns the harness:

```python
# agent.py
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware

from my_service.config.settings import PricingAgentSettings
from my_service.genai.pricing_agent.schemas.output import AgentOutput


def build_agent(*, model, summary_model, tools, settings: PricingAgentSettings):
    return create_agent(
        model=model,
        tools=tools,
        response_format=AgentOutput,
        middleware=[
            SummarizationMiddleware(
                model=summary_model,
                trigger=("tokens", settings.summary_trigger_tokens),
                keep=("messages", settings.summary_keep_messages),
            ),
        ],
    )
```

`bootstrap/` owns when these factories run and supplies settings-derived values,
narrow typed settings objects, and runtime dependencies. Pass only the settings
slice owned by the task, not the application's entire settings object:

```python
# bootstrap/runtime.py
model = build_model(
    model_name=settings.classification_model,
    model_provider=settings.model_provider,
)
classifier = LLMEmailClassifier(model=model)
classify_email = ClassifyEmail(classifier=classifier)

pricing_agent = build_agent(
    model=pricing_model,
    summary_model=summary_model,
    tools=pricing_tools,
    settings=settings.pricing_agent,
)
```

Do not import global settings or construct a model, agent, MCP client,
checkpointer, or other runtime handle at module import time. `config/` loads and
validates settings; `bootstrap/` resolves the selected values and performs the
construction; `llm.py` and `agent.py` own the task-specific construction logic.
This keeps provider selection, overrides, tests, and resource lifecycle under
the composition root.

The response schema comes from `schemas.py` (or `schemas/output.py`), tools from
`tools/`, and prompts from `prompts.py`. `agent.py` never initializes a provider
model itself. Extract a shared constructor only after meaningful construction
policy, rather than model IDs or role configuration, is duplicated across tasks.

Neither setup module is an application entry point, and neither invokes the
model or agent. A sibling capability module such as `classifier.py`,
`generator.py`, `extractor.py`, or `resolver.py` invokes the configured handle,
validates the provider response, translates provider failures into the
application port's failure taxonomy, and returns the typed port result. Name it
after the port capability; do not use generic `adapter.py` or `service.py` by
default. It implements an external capability but does not execute the business
action. Application code calls the port, never the GenAI module directly. Keep all
GenAI modules free of workflow orchestration, deterministic fallback selection,
persistence decisions, and business handoff.

## Classifier versus classification action

The concrete GenAI classifier may:

- assemble provider input from typed business data;
- select the GenAI-owned prompt and invoke the configured model handle;
- validate the provider-facing output schema;
- translate that output into the port's typed candidate;
- translate SDK/provider failures into the port's stable failure contract.

The application classification action may:

- accept or retrieve the email and verify that it is eligible for processing;
- apply deterministic parsing, correlation, or classification policy;
- decide whether an external classifier candidate is required;
- call `EmailClassifier` without knowing whether it is LLM-, rule-, hybrid-, or
  API-backed;
- interpret confidence and labels as a business decision;
- persist state and publish the next business outcome;
- choose action-level retry, defer, replay, or human-review behavior.

Only include behavior the real use case requires. The line is ownership, not a
requirement to manufacture orchestration. Provider mechanics stay in `genai/`;
business decisions and effects sequencing stay in `application/`.

## Dependency direction

```text
API/adapter consumer -> application/email_classification.py
application/email_classification.py -> ports/email_classifier.py
genai/email_classification/classifier.py -> ports/email_classifier.py
bootstrap -> llm.py factory -> configured model
bootstrap -> concrete EmailClassifier implementation -> application action
```

The application action is the public business entry point. It accepts typed business
input plus explicit application context, calls an application port, and returns a
typed business result. The concrete GenAI implementation must not expose provider
message objects, LangGraph internal state, raw JSON, callbacks, or SDK exceptions.

An LLM boundary especially merits a port because it is remote,
nondeterministic, costly, and failure-prone. Put the application Protocol, typed
result, and failure taxonomy in root `ports/`. Let `llm.py` build and bind the
provider model through a factory; when present, let `agent.py` expose the harness
factory. `bootstrap/` calls both and injects the resulting handle into the
capability-named port implementation. Application actions and deterministic
evaluators can then be tested with small fakes.

## Prompts

Prompts are implementation details of the GenAI task, comparable to a query or
wire mapping. Keep them below `genai/<business-task>/`, never in application,
domain, ports, adapters, or core. A prompt may reference typed input assembled by
the GenAI adapter, but must not retrieve configuration or trusted context globally.

Store prompt version beside prompt content or derive both through one prompt
builder. Persist or emit the exact version used where reproducibility requires
it. Promote fragments to `genai/shared/prompts/` only after multiple agents truly
share their semantics; similar wording alone is not enough.

## Tools and MCP

Agent tools are adapters over application ports and application actions:

- validate typed inputs and outputs;
- apply explicit authorization from application context;
- call a port or public application action rather than query the database directly;
- expose bounded behavior and safe error messages;
- keep provider/MCP connection setup outside tool business logic.

`mcp.py` loads and adapts MCP tools for one agent. Shared MCP connection
factories may move to `genai/shared/` after reuse exists. Never let tool discovery
silently broaden the permissions granted by the calling application.

## Retrieval and RAG

Treat RAG as a collaboration of owned responsibilities, not as a mandatory
top-level folder. An agent-facing knowledge-search tool stays in that agent's
`tools.py` or `tools/` while it is local, and calls a public application action
or technology-neutral retrieval port rather than a vector database directly.
When multiple agents genuinely share the same tool contract, promote that tool
to `genai/shared/tools/`.

Keep model-specific retrieval, embedding, reranking, and context-assembly code
inside the owning GenAI task. Promote only behavior with identical semantics to
`genai/shared/retrieval/`. Application-owned ingestion and index-refresh
workflows remain in `application/`; retrieval and vector-index contracts remain
in `ports/`; concrete index persistence remains in `db/` or the repository's
appropriate concrete integration boundary. If retrieval is a standalone GenAI
capability with its own port and lifecycle, prefer a sibling capability such as
`genai/knowledge_retrieval/` over forcing it into `shared/`.

## Middleware and observability

AI middleware owns cross-call mechanics such as attempt budgets, timeout,
fallback, token limits, and agent-specific tracing. General telemetry SDK setup
remains in top-level `observability/`. AI middleware may call those narrow
helpers; top-level observability must not import agents or prompts.

Retries belong at the boundary that can classify provider failures. Business
execution receives a stable transient/permanent failure contract and decides
whether the larger application action should retry, defer, or route to human review.

## Testing shape

Test separately:

- prompt assembly and versioning;
- schema validation and rejection of unexpected output;
- deterministic logic without a provider;
- model and agent factories without global configuration or import-time handles;
- capability invocation and caller-side error translation with a fake model
  handle;
- graph routing and nodes with fake ports;
- bootstrap wiring independently from application and GenAI behavior;
- authorization/context propagation into tools without prompt-derived trust.

Do not make live model calls part of the ordinary unit suite.
