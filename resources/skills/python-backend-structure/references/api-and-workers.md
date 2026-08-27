# API, worker, and event-driven process templates

## FastAPI / HTTP API

```text
src/<package>/
├── main.py
├── bootstrap/
│   ├── app.py                      # create_app(), lifespan, ASGI app
│   └── runtime.py                  # Dependency graph and disposal
├── api/
│   ├── dependencies.py             # Request-scoped dependency adapters
│   ├── exception_handlers.py       # Business error -> HTTP response
│   ├── middleware/
│   │   ├── authentication.py
│   │   ├── context.py
│   │   └── request_logging.py
│   ├── routers/
│   │   ├── health.py
│   │   └── tickets.py
│   └── schemas/
│       └── tickets.py              # HTTP-only request/response contracts
├── application/
├── domain/                         # When shared business concepts exist
├── ports/
├── adapters/
├── genai/                          # Mandatory when any GenAI exists
├── config/
├── db/
└── observability/
```

`bootstrap/app.py` owns the FastAPI instance, lifespan, router registration,
and framework instrumentation. Keep `api/` focused on the HTTP transport.

Routers should:

1. validate and translate HTTP input;
2. resolve request/application context;
3. call one public application action;
4. translate the result to an HTTP response.

Routers must not execute SQL, initialize clients, invoke LLM SDKs directly, or
contain business branching. Keep transport-specific Pydantic models in
`api/schemas/`; keep reusable application contracts in `ports/` and business
types in `domain/`.

Use `api/routers/` whenever the service exposes application routes, even if it
starts with one module; this is a deliberate stable location. Create
`api/middleware/`, `api/schemas/`, and other branches when those responsibilities
exist—do not commit empty packages merely to complete the drawing.

Middleware is for cross-request transport mechanics such as authentication
extraction, correlation context, CORS, request logging, and size limits. It is
not a hidden application layer. Authorization decisions that depend on domain
state belong to the relevant application action.

## Long-running worker

```text
src/<package>/
├── main.py
├── bootstrap/
│   ├── runtime.py                  # Construct resources
│   └── supervisor.py               # Start/stop loops and task health
├── application/
│   ├── process_due_work.py         # Business action
│   └── submit_batch.py             # Independent business action
├── adapters/
│   └── scheduler/
│       └── trigger.py              # Translate an external tick, when needed
├── ports/
├── config/
├── db/
└── observability/
```

The supervisor owns `asyncio` tasks, stop events, graceful shutdown, and task
health. An adapter owns external trigger translation. Business stage order and
decisions remain in an application action.

For a scheduled batch that runs once and exits, omit the supervisor. `main.py`
enters the runtime context, invokes the application action once, maps the outcome
to an exit code, and exits.

## SQS, Kafka, or another broker

Broker code is a concrete inbound or outbound adapter. Keep it below root
`adapters/`, grouped by provider or technology; do not create root `messaging/`:

```text
src/<package>/
├── adapters/
│   └── aws/
│       ├── sqs_consumer.py          # Poll/receive/ack/nack boundary
│       ├── sqs_serialization.py     # AWS wire-envelope translation
│       └── sqs_publisher.py         # Only when publishing is used
├── bootstrap/
│   └── supervisor.py
├── application/
│   └── email_admission.py
└── ports/
    └── message_publisher.py         # Only if an application action publishes
```

Use `adapters/kafka/` for Kafka or `adapters/rabbitmq/` for RabbitMQ. Delivery
types and heartbeat contracts used only inside the adapter remain private
there; promote only application-facing contracts to root `ports/`.

Keep `adapters/aws/` flat while the selected SQS/S3 integration is only a few
modules. If SQS later grows separate consumer, publisher, serialization,
heartbeat, and DLQ policies, promote that slice to `adapters/aws/sqs/`; do the
same independently for S3. Do not introduce provider subpackages before their
contents have a distinct reason to change.

The transport boundary owns:

- polling and delivery batches;
- wire-envelope parsing and validation;
- trace-context extraction/injection;
- visibility heartbeat, offset commit, acknowledgement, and redelivery mapping;
- poison-message/DLQ decisions that are transport policy.

The application action owns:

- authentication or authorization rules based on business evidence;
- idempotency semantics and durable admission decisions;
- classification and correlation;
- state transitions and downstream business handoff.

Translate application outcomes into ack/retry/dead-letter behavior at the consumer
adapter boundary. Do not let SQS receipt handles or Kafka partition offsets
enter application, domain, or ports.

## Hybrid API plus worker

A single deployable may expose health/admin HTTP endpoints and run background
consumers. Keep one shared composition root:

```text
main.py
bootstrap/
├── app.py
├── runtime.py
└── supervisor.py
api/
application/
ports/
adapters/
genai/                              # When any GenAI exists
```

FastAPI lifespan may enter `runtime()` and start `supervisor`, but application and
domain remain framework-independent. If API and worker become independently
scaled or deployed processes, split them into separate service packages and
extract only stable shared contracts/logic to an internal library.

## Health and readiness

Health state may be shared by API routes and the supervisor, but its ownership
must be explicit. Liveness reports process life. Readiness reflects whether the
process can accept useful work: initialized dependencies, compatible schema,
healthy progress, and required external availability according to service
policy. Health probes must not perform business work.
