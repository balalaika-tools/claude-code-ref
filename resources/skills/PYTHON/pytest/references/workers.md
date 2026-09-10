# Workers, task queues, and consumers

Use this reference for Celery, RQ, broker consumers, scheduled jobs, and other
background processes. Preserve the installed worker/broker versions and the
production execution pool when selecting tools and smoke tests.

## Separate application behavior from delivery mechanics

Keep the worker entry point thin. It should own transport-specific concerns:

- deserialize and validate the envelope;
- resolve IDs into current state rather than accepting large serialized domain
  objects;
- establish request/correlation context;
- call an ordinary application action;
- classify retryable, terminal, reject, and dead-letter outcomes;
- expose stable result or acknowledgement behavior.

Put business decisions in an ordinary callable with explicit ports. Test that
callable exhaustively without starting a worker. Then test the thin task or
consumer adapter for serialization, headers, retry translation, and delivery
policy. Finally, use a real worker and broker for the mechanics no in-process
double can prove.

| Boundary | What it proves |
| --- | --- |
| Application unit | Business invariants, durable-effect decisions, idempotency policy, error classification |
| Task/consumer adapter unit | Argument conversion, envelope validation, context, selected retry/reject call, task options |
| Repository integration | Queries, constraints, transactions, locking, deduplication, outbox behavior |
| Embedded worker integration | Registration, representative serialization/routing, basic retry execution |
| Production-like process smoke | Actual broker/backend, worker pool, fork/startup, acknowledgements, crash/redelivery |

Do not reproduce the entire business decision table through a worker. Do not
claim delivery confidence after directly calling the task function.

## Do not treat eager or synchronous mode as a worker

Celery explicitly states that `task_always_eager` is an emulation with
discrepancies from worker execution and is not suitable evidence for worker
correctness. It can bypass or alter serialization, routing, process isolation,
acknowledgements, retry scheduling, and result-backend behavior.

The same distinction applies to other queues. RQ's synchronous queue bypasses a
worker, and its `SimpleWorker` omits production mechanics such as `fork()` and
heartbeats. Such modes can be useful for a narrow application or wiring test,
but name what they prove.

## Celery test environments

- `celery.contrib.pytest` provides mock-based and embedded-worker fixtures for
  unit/integration feedback.
- `pytest-celery` provides Docker-based, production-like smoke infrastructure.
- Celery documents these APIs as incompatible. Do not enable both in one suite
  and assume their fixtures or configuration compose.
- Use the actual production worker pool in at least a release or smoke test when
  pool behavior matters. Alternative pools can disable features such as soft
  timeouts or `max_tasks_per_child`.
- Bound every `AsyncResult.get()` and worker wait. The official examples use a
  timeout; an unbounded result wait can hang CI indefinitely.

Do not add either plugin merely because an example uses it. First inspect the
repository's existing worker harness, Docker topology, and supported broker.

## Retry and acknowledgement are different contracts

Treat these mechanisms separately:

- A task retry handles an expected catchable failure by publishing another
  attempt, normally with the same task ID and routing destination. Celery's
  `Task.retry()` raises its `Retry` sentinel by default, so code after it is not
  reached. `throw=False` changes that control flow; inspect and test the behavior
  the task actually configures.
- Late acknowledgement addresses loss before acknowledgement, such as a worker
  or connection failure. It is not an automatic retry policy for ordinary task
  exceptions.
- Publisher confirms and consumer acknowledgements solve different delivery
  risks. A broker may redeliver, so consumers must tolerate duplicates when the
  chosen guarantees permit them.

Test retry policy without wall-clock waits:

- transient exceptions request retry with the original cause and intended
  limit/backoff parameters;
- validation or permanent failures do not retry;
- retry exhaustion reaches the promised failed, compensated, alerted, or
  dead-letter outcome;
- with the default `throw=True`, effects after `retry()` are unreachable; if the
  task deliberately uses `throw=False`, test the resulting state and control
  flow explicitly;
- production jitter and delay policy are configured as intended, while test
  configuration may shorten or remove delay only inside the worker test.

Add at least one real-worker transition when retry scheduling is operationally
important: a controlled first attempt fails, the broker schedules another, the
next attempt succeeds, and final durable state is correct.

## Prove idempotency as durable state

Do not define idempotency as "the mock was called once." Deliver the same
operation more than once and assert one business outcome.

High-value cases include:

- sequential duplicate delivery;
- concurrent duplicate delivery through separate database sessions;
- failure after the durable effect but before acknowledgement;
- retry after a timeout whose external outcome is unknown;
- outbox relay redelivery;
- reuse of the same provider idempotency key across attempts.

Prefer a durable uniqueness or idempotency record keyed by a business operation
or `(consumer, event_id)`. Assert the final ledger/object/outbox state through a
fresh session and, when relevant, the stable key sent to the irreversible
provider.

If late acknowledgement or reject-on-worker-loss is relied on, include a
production-like destructive smoke that kills the correct worker child at a
controlled point and proves redelivery is harmless. Isolate it behind an
explicit destructive marker and bounded teardown. Celery warns that careless
requeue/worker-loss settings can create infinite message loops.

Name the fault being reproduced: task child exit, worker parent exit, broker
connection loss, host/container loss, and timeout-driven visibility redelivery
can have different acknowledgement behavior across pools, transports, and
settings. Reproduce the incident's failure mode first; do not infer one from a
different kill test or from `task_reject_on_worker_lost` configuration alone.

## Minimum delivery matrix

Select the cases the service actually promises:

1. production imports discover and register the task or consumer;
2. an actual broker round trip preserves the supported serialized envelope;
3. queue, routing key, priority, headers, correlation ID, and idempotency ID are
   correct where downstream behavior depends on them;
4. success produces the intended durable outcome;
5. a transient failure retries and can recover;
6. a permanent failure does not retry;
7. exhaustion reaches the final failure or dead-letter policy;
8. duplicate delivery is harmless;
9. worker loss/redelivery matches acknowledgement settings when required;
10. process startup and child initialization create safe database and network
    resources;
11. periodic jobs cannot overlap when the business contract forbids it;
12. poison messages cannot create an unbounded requeue loop.

Do not implement all twelve ceremonially. Map each selected case to a real
production guarantee or failure mode.

## Database and publication boundaries

A worker runs in another connection and often another process:

- It cannot see uncommitted setup from the test process under normal transaction
  isolation.
- Its commits cannot be rolled back by the test process's outer transaction.
- It must not inherit a live pooled database connection across `fork()`.

Use committed setup plus a disposable database/schema/tenant and unique queue or
namespace. Stop workers before cleanup. Re-read results using a fresh session.
Use one SQLAlchemy session per thread or task.

Test message publication relative to the database transaction:

- no publication or visible outbox entry after rollback;
- publication or relay occurs after commit, when referenced rows are visible;
- the atomic database change plus outbox insert survives failure together;
- a duplicate relay is safe for the consumer.

With Celery 5.4+ Django integration, `DjangoTask.delay_on_commit()` can prevent a
worker from racing an uncommitted row. It returns no task ID immediately, and a
custom task base must preserve the relevant `DjangoTask` behavior. In other
versions or stacks, use the repository's after-commit mechanism or transactional
outbox and test that behavior directly.

For prefork workers, a production-pool smoke should ensure parent-process pools
are disposed or recreated in children. This is different from a task unit test.

## Broker-specific semantics

Use the production broker family for the delivery properties being claimed. An
in-memory transport cannot prove RabbitMQ acknowledgement, Redis/SQS visibility,
or actual serialization behavior.

- For Redis or SQS, compare visibility timeout with task runtime, ETA/countdown,
  and retry delays. A task exceeding visibility may be redelivered. Test a
  shortened representative scenario only when the service depends on it.
- For RabbitMQ, cover publisher confirmation and consumer redelivery separately
  where guaranteed publication matters.
- Use unique broker vhosts, namespaces, queues, or routing keys per test worker
  and xdist worker. Purging a shared queue is not isolation.
- Capture broker/worker logs, task IDs, queue names, attempt numbers, and
  correlation IDs as failure artifacts.

## Generic stream and batch consumers

For Kafka-like streams, custom polling loops, and batch consumers, also select
the guarantees the application relies on:

- commit an offset or acknowledge only at the intended durable-effect boundary;
- recover safely when a consumer-group rebalance or process shutdown interrupts
  a batch;
- preserve partition/key ordering only when the business contract requires it,
  and test parallel partitions without assuming global order;
- define partial-batch behavior so one poison record cannot silently drop good
  records or create an infinite replay loop;
- drain or cancel in-flight work safely on shutdown;
- exercise backpressure, prefetch, lease/heartbeat, or maximum-poll settings
  when they can cause duplication or eviction;
- use the configured serializer against trusted input. RQ's default pickle-based
  payloads and any other executable serializer must never be treated as safe for
  untrusted producers;
- redact sensitive payloads from failure artifacts, dead-letter records, and
  logs while retaining correlation data needed to debug the test.

Test offset/acknowledgement, effect, and failure as one state transition rather
than as independent mock call counts.

## Scheduled and periodic work

- Prove schedule configuration or next-run calculation without sleeping until a
  cron boundary.
- Cover timezone and DST boundaries if the schedule is business-significant.
- Ensure only the intended scheduler instance publishes the schedule.
- If executions may overlap, test the application as concurrent work. If
  overlap is forbidden, run two independent lock/lease contenders and assert
  one durable owner plus safe expiry/recovery.
- Test lease expiry with an injected clock or short bounded integration setup,
  not an arbitrary long sleep.

## Concurrency and time

Coordinate workers, threads, and tasks with events, barriers, database locks, or
observable state. Every wait gets a timeout. Do not make precise millisecond
assertions about a distributed scheduler; express "not before" and "eventually
before a deadline" with justified tolerance.

Freezing time in pytest does not advance a broker or worker container. Test
broker ETA/countdown behavior with short real durations in a marked worker job,
and keep pure backoff calculations under an injected clock/random source.

## Suggested CI shape

Use this to review or propose profile placement. Change CI files only when that
configuration work is part of the requested scope.

- **PR:** pure/application tests, task-adapter tests, real database repository
  tests, contract tests, and a bounded embedded-worker path if reliable.
- **Main or release:** production broker/backend, migrations, actual worker pool,
  registration, serialization, retry, and startup smoke.
- **Nightly or explicit destructive:** concurrent duplicates, child kill and
  redelivery, visibility timeout, scheduler overlap, and longer stateful tests.

Run only versions and brokers the product supports. Never hide a flaky worker
test behind automatic reruns; preserve diagnostics and repair its isolation or
synchronization.

## Primary references

- [Celery testing guide](https://docs.celeryq.dev/en/stable/userguide/testing.html)
- [pytest-celery production-like testing](https://docs.celeryq.dev/projects/pytest-celery/en/stable/)
- [Celery task retries, idempotency, and late acknowledgements](https://docs.celeryq.dev/en/stable/userguide/tasks.html)
- [Celery retry versus late acknowledgement](https://docs.celeryq.dev/en/main/faq.html#should-i-use-retry-or-acks-late)
- [Celery concurrency pools](https://docs.celeryq.dev/en/stable/userguide/concurrency/index.html)
- [Celery configuration](https://docs.celeryq.dev/en/stable/userguide/configuration.html)
- [Celery Redis visibility timeout](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html#visibility-timeout)
- [Celery periodic tasks](https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html)
- [Celery Django transaction integration](https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html#trigger-tasks-at-the-end-of-the-database-transaction)
- [RQ testing](https://python-rq.org/docs/testing/)
- [RQ worker behavior](https://python-rq.org/docs/workers/)
- [Apache Kafka delivery semantics](https://kafka.apache.org/documentation/#semantics)
- [RabbitMQ reliability](https://www.rabbitmq.com/docs/reliability)
- [RabbitMQ acknowledgements and redelivery](https://www.rabbitmq.com/docs/confirms)
- [SQLAlchemy connection pools with multiprocessing or `fork()`](https://docs.sqlalchemy.org/en/20/core/pooling.html#using-connection-pools-with-multiprocessing-or-os-fork)
- [PostgreSQL transaction visibility](https://www.postgresql.org/docs/current/transaction-iso.html)
- [Transactional outbox pattern](https://microservices.io/patterns/data/transactional-outbox.html)
