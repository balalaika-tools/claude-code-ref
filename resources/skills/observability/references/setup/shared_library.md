# Shared observability library

Use this reference only when the user explicitly asks to create, extract, or
change a reusable observability package consumed by multiple deployables. For a
normal service-local instrumentation task, keep the one-service scope in
`SKILL.md`.

## Read next

- Read `package_layout.md` for settings ownership and service-local placement.
- Read `sdk_bootstrap.md` for provider construction, startup, and shutdown.
- Read `../logging/structlog.md` when logging configuration or processors are
  part of the shared package.
- Read `../testing.md` before implementing deterministic helpers or migration
  contracts, and `../verification.md` last.
- In a uv workspace, use the `python-uv-workspace-monorepo` skill for member,
  dependency, lockfile, scoped-install, and Docker mechanics. Use
  `python-backend-structure` for the internal modularization of `libs/*`.

## The package must earn the boundary

Do not create a package merely because two files look similar. Extract only a
cohesive contract that has demonstrated reuse across current deployables and
the same operational meaning in each consumer. A library is justified when it
removes duplicated policy or lifecycle behavior without importing one
service's business model into the others.

Good shared responsibilities include:

- process-scoped OpenTelemetry provider construction and bounded shutdown;
- OTLP endpoint resolution and resource construction from explicit inputs;
- trace-context normalization, injection, extraction, and linked-root helpers;
- safe span context managers and narrowly scoped decorators;
- trace/log correlation, common JSON rendering, redaction, and environment-
  scoped exception projection;
- stable cross-service semantic constants whose meaning is genuinely shared.

Keep these service-local unless a stable cross-service contract already exists:

- business span names, workflow states, outcomes, and reason taxonomies;
- service metric instruments, histogram views, and business log event names;
- framework, vendor, browser, database, or GenAI instrumentation used by only
  one consumer;
- settings models, environment lookup, and deployment-specific policy;
- exporter filters or sampling decisions that intentionally differ by service.

## Ownership split

```text
shared observability package
  generic SDK lifecycle, spans, propagation, resource helpers
  common structured-logging processors and safety policy

service config/
  validates environment and constructs the service-specific config value

service bootstrap/
  explicitly configures logging/telemetry and owns shutdown order

service observability/
  service vocabulary, instruments, projections, and integration adapters

application boundary
  decides business outcome and supplies attributes known only after execution
```

The shared package must not import a deployable's private package, settings
class, application action, domain type, or test helper. Accept typed values or a
library-owned frozen configuration object at the public boundary. Do not read
environment variables inside the library.

## Suggested package growth

Start flat and create only modules with a current responsibility:

```text
src/company_observability/
├── __init__.py          # small intentional public API
├── config.py            # library-owned input values, no environment reads
├── providers.py         # provider construction and lifecycle
├── spans.py             # context managers and optional decorators
├── propagation.py       # bounded W3C carriers and links
└── logging.py           # shared processors/configuration, when justified
```

Do not create `tracing/`, `metrics/`, `logging/`, `exporters/`, or `plugins/`
subpackages in advance. Promote one slice only when it contains several
cohesive modules, evolves independently, or needs distinct tests. The general
library foldering rules live in the `python-backend-structure` skill.

Keep `__init__.py` deliberate. Re-export the small supported API, not every SDK
type or internal helper. Consumers should not depend on the package's private
module layout.

## Explicit lifecycle

Importing the package must be inert:

```python
import company_observability  # no provider, logger, or instrumentation side effect
```

Each process configures it explicitly from its composition root:

```python
providers = configure_observability(config, metric_views=service_views)
configure_logging(logging_config, logger_provider=providers.logger_provider)
```

Apply these invariants:

- one provider owner per process; never mix code-owned and zero-code setup;
- initialization is idempotent for the same effective configuration;
- a second incompatible configuration fails explicitly instead of silently
  returning providers stamped with the wrong service identity;
- provider handles are returned to bootstrap rather than hidden behind imports;
- shutdown is idempotent, bounded where the runtime requires it, and runs after
  clients/background work stop;
- telemetry export or shutdown failures do not replace the business result;
- process-wide instrumentation is installed explicitly and at most once.

Expose narrowly typed extension inputs such as metric views, a sampler, or a
span-exporter wrapper only when current consumers need them. Do not build a
plugin/factory system around hypothetical service differences. Framework- and
vendor-specific integrations stay outside the generic provider module.

## Spans: context manager first

The primary helper is a context manager because callers often add attributes,
links, status, and business outcome during execution. It must start the span
with `record_exception=False` and `set_status_on_exception=False`, apply the
error contract from `../conventions/errors.md`, and re-raise exceptions.

A decorator may wrap a stable synchronous or asynchronous execution boundary
when its span name and initial attributes are available before the call. It is
only convenience over the same context manager: preserve the wrapped signature
and metadata, do not instrument arbitrary helper functions, and do not hide
outcome handling that belongs in the caller. A decorator or context manager
cannot detect an exception swallowed inside the wrapped body; handled terminal
failures must mark the active span explicitly.

The generic helper may set standard failure status and bounded `error.type`.
It must not guess a service's `app.outcome`, retry classification, HITL state,
or metric labels. A thin service-local wrapper may add those semantics.

## Shared structured logging

Logging belongs in the same shared package when multiple services use the same
transport, JSON schema, trace-correlation fields, redaction rules, and exception
detail policy. Sharing only a `get_logger()` call while each service has a
different processor chain is not a useful abstraction.

The shared logging module may own:

- stdlib/structlog processor construction and level normalization;
- current-span `trace_id`/`span_id` injection;
- credential/token redaction and safe/full exception projection;
- stable common fields such as timestamp, severity, and service identity;
- optional named OTel log-event export when it has one delivery owner.

It must remain inert on import. Bootstrap passes the service name, level,
exception-detail policy, output stream, and optional `LoggerProvider` into an
explicit `configure_logging(...)` call. Do not bind one service identity into a
module-global logger at import time.

Business event names and fields remain at the call site or in the service's
observability package. The shared processor enforces shape and safety; it does
not decide which business event occurred. Preserve one delivery owner: stdout
collection and OTLP log export must not both emit the same record.

## Migration

1. Inventory all candidate consumers, public imports, settings, provider
   ownership, shutdown behavior, logging paths, and tests.
2. Separate true common invariants from similar-looking service policy. Resolve
   incompatible semantics before extracting them; do not bury them in flags.
3. Extract the smallest stable slice into the library with focused unit tests.
4. Keep a thin service-local compatibility facade when imports cannot move
   atomically.
5. Migrate and verify one consumer at a time, including its package-scoped
   install and startup/shutdown tests.
6. Remove duplicated service code only after every intended consumer has moved.

The shared change stays additive until the migration is complete. Do not update
unrelated services merely to make their folder trees symmetrical.

## Verification

- Importing the library creates no providers, instruments, or logging handlers.
- Same-config initialization is idempotent; conflicting initialization is
  rejected deterministically.
- Success, escaping failure, handled failure, cancellation, and linked-root
  behavior satisfy the common contract.
- Logging inside a span has valid trace/span identifiers and applies the same
  redaction and environment exception policy in every consumer.
- A record has one delivery path; a boundary has one span owner.
- Shutdown flushes each enabled signal once and cannot replace business failure.
- Library tests pass independently, then each migrated consumer's contract and
  startup/lifecycle tests pass under a package-scoped install.
