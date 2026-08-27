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

## Full multi-agent shape

```text
<package>/
└── genai/
    ├── shared/                     # Create only after demonstrated reuse
    │   ├── prompts/                # Stable shared prompt fragments
    │   ├── tools/                  # Tools used by multiple agents
    │   ├── middleware/             # Shared limits, tracing, retry, fallback
    │   ├── llms/                   # Shared provider/model factories
    │   └── schemas/                # Reused AI-specific typed contracts
    │
    ├── pricing_agent/
    │   ├── graph/
    │   │   ├── graph.py            # Build and compile StateGraph
    │   │   ├── nodes.py            # Node implementations
    │   │   ├── state.py            # Mutable graph execution state
    │   │   └── routing.py          # Conditional edges and routing
    │   ├── prompts/
    │   │   ├── system.py
    │   │   └── pricing.py
    │   ├── tools/
    │   │   ├── products.py
    │   │   └── pricing.py
    │   ├── middleware/
    │   │   ├── retry.py
    │   │   ├── tracing.py
    │   │   └── stack.py
    │   ├── schemas/
    │   │   ├── input.py
    │   │   ├── output.py
    │   │   └── tool_schemas.py
    │   ├── contracts.py            # GenAI-private contracts, when needed
    │   ├── mcp.py                  # MCP setup only when used
    │   ├── checkpointer.py         # Persistence only when graph needs it
    │   ├── llm.py                  # Model construction/binding only
    │   ├── agent.py                # Agent init: builds and exports the harness
    │   │                           # (configured model + tools + middleware)
    │   └── pricer.py               # Capability-named port implementation
    │
    └── resolution_agent/
        ├── graph/
        │   ├── graph.py
        │   ├── nodes.py
        │   ├── state.py
        │   └── routing.py
        ├── prompts/
        │   └── system.py
        ├── tools/
        │   └── exceptions.py
        ├── schemas/
        │   ├── input.py
        │   ├── output.py
        │   └── tool_schemas.py
        ├── contracts.py
        ├── middleware.py           # File is enough when behavior is simple
        ├── llm.py
        ├── agent.py
        └── resolver.py             # Capability-named port implementation
```

This is a destination for a genuinely complex AI application, not starter
boilerplate. Do not create `graph/`, `tools/`, `middleware/`, `mcp.py`, or
`checkpointer.py` when the GenAI task does not use them.

## Simple structured-model task

Most backend AI integrations should start smaller:

```text
genai/
└── email_classification/
    ├── prompts.py                  # Prompt definitions/builders
    ├── schemas.py                  # AI-facing input/output schemas
    ├── llm.py                      # Model construction/binding only
    └── classifier.py               # EmailClassifier implementation
```

These four modules are the stable baseline for a structured-model capability;
do not merge them to reduce file count. Keep them flat while small. Split
`prompts.py` into `prompts/system.py` and task-specific modules, or `schemas.py`
into `schemas/input.py`, `output.py`, and `tool_schemas.py`, only after the
narrower area has several real files. Apply this flat-first growth rule
throughout `genai/`.

## `llm.py` and optional `agent.py`

Every GenAI task has `llm.py`; never move model construction into the capability
implementation. A bare model task invokes the handle exported by `llm.py`. An
agent task additionally has `agent.py`, which imports that configured model and
builds the agent harness. Never name model construction `model.py` or
`models/`—those read as domain entities.

`llm.py` initializes the provider model for every GenAI task and binds what makes
it callable—structured output, tools, timeouts, and limits—then exports the bound
model:

```python
# llm.py
from langchain.chat_models import init_chat_model

from .schemas import ClassificationOutput

model = init_chat_model(
    model="gpt-5.4",
    model_provider="openai",
).with_structured_output(ClassificationOutput)
```

`agent.py` is added when the GenAI task is an agent. It imports the configured
models from `llm.py` and wires them into a harness with tools, response format,
and middleware, then exports the compiled agent:

```python
# agent.py
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware

from .llm import model, summary_model
from .schemas.output import AgentOutput
from .tools import get_product_price

agent = create_agent(
    model=model,
    tools=[get_product_price],
    response_format=AgentOutput,
    middleware=[
        SummarizationMiddleware(
            model=summary_model,
            trigger=("tokens", 4000),
            keep=("messages", 20),
        ),
    ],
)
```

Both are setup-only modules. The response schema comes from `schemas.py` (or
`schemas/output.py`), the tools from `tools/`, and prompts from `prompts.py`.
`llm.py` constructs models; `agent.py` constructs the harness from those models
and never initializes a provider model itself. Shared factories may live in
`genai/shared/llms/` after demonstrated reuse, but every task still keeps its own
`llm.py` as the task-level construction/binding entry point.

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
genai/email_classification/classifier.py -> llm.py -> provider schemas
bootstrap -> application action + concrete EmailClassifier implementation
```

The application action is the public business entry point. It accepts typed business
input plus explicit application context, calls an application port, and returns a
typed business result. The concrete GenAI implementation must not expose provider
message objects, LangGraph internal state, raw JSON, callbacks, or SDK exceptions.

An LLM boundary especially merits a port because it is remote,
nondeterministic, costly, and failure-prone. Put the application Protocol, typed
result, and failure taxonomy in root `ports/`. Let `llm.py` build and bind the
provider model; when present, let `agent.py` build the harness from that model.
The capability-named sibling implements the port and translates provider
failures. Application actions and deterministic evaluators can then be tested with
small fakes.

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
- model construction/binding, and caller-side error translation, with a fake
  model handle;
- graph routing and nodes with fake ports;
- bootstrap wiring independently from application and GenAI behavior;
- authorization/context propagation into tools without prompt-derived trust.

Do not make live model calls part of the ordinary unit suite.
