# Focused views: service internals and cross-service flows

Use only after **Focused view** is selected in the interaction workflow. This is one general capability: agents, ingestion, authentication, indexing, payments and other domains are subjects, not new diagram types.

## Scope and detail

Confirm one of: a single service's internals, a collaborating group of services, or a named flow traversing services. A small scope is not automatically a focused view: an overview of two services still shows their main responsibilities and interface.

Focused means exposing useful internal components or stages, not enlarging an overview card. Preserve requested depth and provider presentation independently. A focused AWS view may retain meaningful product details while omitting unrelated networking; a neutral focused view may name PostgreSQL, NATS or Langfuse if the user wants those technologies.

Start with entry/exit points and the concrete question the view answers. Trace handlers, orchestration/agent graphs, processing stages, tool registrations, client adapters, state transitions and actual calls. Distinguish synchronous calls, asynchronous work and side effects. Keep file/line evidence in working notes. Labels should explain responsibilities, not reproduce source expressions.

## Boundaries and context

- Use a named **service boundary** around internal component/stage cards. A parser, guardrail, agent or MCP client library inside a service is not automatically a separate deployable service.
- For multiple services, retain distinct service boundaries and show which components call across them. Internal tools and MCP servers are not interchangeable: a server exposes tools, while client sessions belong to the caller unless separately deployed.
- Components outside the confirmed scope remain compact external dependency cards. Do not expand their implementation or add provider plumbing just because it exists elsewhere in the repo.
- Preserve names and interface direction from any related overview; the focused view should explain that overview, not contradict it. Different cardinality is expected when a service card expands into internal components.
- In the XML, boundaries stay decorative root-coordinate vertices and component cards use the shared outer-card endpoint contract. Optional `archKind=stage|component|service|external` and `archService=<boundary-id>` metadata can clarify semantic roles; these are documentation metadata, not a substitute for evidence or visual labels.

## Example: ingestion service

Read [focused-ingestion-service.drawio](../assets/examples/focused-ingestion-service.drawio) for a single-service pipeline. It shows validation, parsing, normalization, chunking and indexing inside one service; input, embedding endpoint and vector storage are external context. Rejected records and checkpoints are meaningful branches. These are a labeled illustrative proposal, not assumed features of every ingestion service.

For a real request, find the actual stages and useful branches. Add batching, queues, retries, dead-letter handling or embeddings only if requested/evidenced and relevant to the chosen flow. Preserve streaming/parallel behavior; do not manufacture a serial pipeline. Keep SQL, payload schemas and retry constants out unless they explain the requested mechanism clearly.

## Example: Agent Service + MCP Service

Read [focused-agent-mcp-services.drawio](../assets/examples/focused-agent-mcp-services.drawio) for collaboration across service boundaries. Within Agent Service it expands input/output guardrails, orchestrator, research/execution sub-agents, state and trace export. Within MCP Service it shows the MCP server and business-tool adapters. External model/API calls are visible, and offline evaluation consumes saved traces and curated cases separately from request execution.

For a real system, inspect agent definitions, delegation and result handling, tools, MCP client/server registration, model clients, shared context/state, guardrail enforcement, telemetry instrumentation and evaluation jobs. Show who calls which tools; don't connect every agent to every tool. Distinguish an LLM sub-agent from a deterministic worker. Inspect where guardrails run; don't assume a box protects every path. Observability is a side effect; offline evals are not a request-path gate. Online evals belong on the live path only when the implementation makes them one. None of these features is mandatory when absent from the requested/evidenced architecture.

## Acceptance before delivery

Check against the confirmed brief, independently of XML geometry:

1. Does the diagram expose the requested internals/flow rather than one opaque service card?
2. Are all included stages/components supported or labeled assumptions, with forbidden sources excluded?
3. Are real service boundaries distinct from internal modules and logical grouping?
4. Are external dependencies concise, and names/interfaces consistent with the overview?
5. Are branch/return/async/telemetry/evaluation relations distinguishable without unreadable labels?
6. Is the focus recognizable in the title/subtitle, and is the remaining detail readable at the intended scale?

Number meaningful explanatory stages; don't imply a total order among concurrent branches or side effects. Increase canvas size or split explicitly requested views into pages before shrinking text. Do not generate extra overview/detail pages the user did not ask for.

## Visual hierarchy

Apply the shared boundary-header icon convention to named service frames and meaningful offline subsystems. Color component cards by responsibility, consistently across services: for example blue for validation/policy, orange for transformation/coordination, teal for model/agent work, purple for state/integration, rose for rejection/telemetry, green for offline evaluation and gray for generic external callers. These are adaptable examples, not a requirement to use every color. Related stages share a color; do not assign a new hue to every node or make all cards the same blue. Use lighter, quieter fills on enclosing frames and stronger card accents, keeping labels/icons legible. Color supplements names and boundaries; it does not imply deployment ownership or replace flow semantics.
