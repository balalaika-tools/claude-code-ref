# Development and Staging Collector Configuration

Development and staging optimise for **debugging visibility**, not cost. That means:

```
no trace sampling
no unnecessary filtering
full metrics
```

If you cannot reproduce a production incident in staging because staging sampled the trace away, the environment failed at its job. Add sampling to a lower environment only when telemetry volume genuinely makes it impractical, and say so in the config comments.

---

## Development

Small limits, a debug exporter you can actually read, no credentials.

```yaml
# services/otel-collector/config.dev.yaml
extensions:
  health_check:
    endpoint: 0.0.0.0:13133

receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 256
    spike_limit_mib: 64

  resource/environment:
    attributes:
      - key: deployment.environment.name
        value: development
        # insert, not upsert: never overwrite a value the service set itself.
        action: insert

  batch:
    timeout: 1s          # short, so spans appear while you are still looking
    send_batch_size: 128

exporters:
  # Prints telemetry to the Collector log. Invaluable locally, never in prod.
  debug:
    verbosity: detailed
    sampling_initial: 5
    sampling_thereafter: 200

  otlphttp/traces:
    endpoint: ${env:TRACES_ENDPOINT}

  otlphttp/metrics:
    endpoint: ${env:METRICS_ENDPOINT}

service:
  extensions: [health_check]
  telemetry:
    # This resource belongs to the Collector itself. The
    # resource/environment processor below labels telemetry passing through it.
    resource:
      attributes:
        - name: service.name
          value: otel-collector-gateway
        - name: deployment.environment.name
          value: development
    logs:
      level: info
      encoding: console
    metrics:
      level: normal
      readers:
        - periodic:
            # Bound the final shutdown export inside the 30 s Compose budget.
            timeout: 5000
            exporter:
              otlp:
                protocol: http/protobuf
                endpoint: ${env:SELF_METRICS_ENDPOINT}
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, resource/environment, batch]
      exporters: [debug, otlphttp/traces]

    metrics:
      receivers: [otlp]
      processors: [memory_limiter, resource/environment, batch]
      exporters: [debug, otlphttp/metrics]

    logs:
      receivers: [otlp]
      processors: [memory_limiter, resource/environment, batch]
      exporters: [debug]
```

Notes on the choices:

- **No sampling processor at all.** Every trace is kept.
- **`debug` with `verbosity: detailed`** prints full spans. The `sampling_*` settings stop a busy local run from flooding the terminal. It prints *everything on the span*, so with `CAPTURE_AI_CONTENT` enabled it writes prompts and completions into the Collector's own logs — do not point a log shipper at a Collector running this exporter, and do not enable it anywhere with real user content.
- **Application and self-metrics both leave by push.** The debug exporter gives
  local visibility; the configured OTLP destinations prove delivery.
- **Short batch timeout.** Five seconds feels broken when you are watching a terminal for a span you just triggered.
- **`memory_limiter` is still present.** It is cheap, and its absence in dev is how you discover in production that nobody ever tested with it.

### Compose

```yaml
# compose.yaml
services:
  otel-collector:
    build:
      context: ./services/otel-collector
      args:
        CONFIG_FILE: config.dev.yaml
    restart: unless-stopped
    ports:
      # Loopback only: nothing on the network can inject telemetry.
      - 127.0.0.1:4317:4317
      - 127.0.0.1:4318:4318
      - 127.0.0.1:13133:13133
    stop_grace_period: 30s
```

Services on the same Compose network export to `http://otel-collector:4318`, not the host mapping.

---

## Staging

Staging should be production's shape with production's *retention* behaviour removed. Same processors, same exporters, same redaction — no sampling.

```yaml
# services/otel-collector/config.staging.yaml
extensions:
  health_check:
    endpoint: 0.0.0.0:13133

receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 512
    spike_limit_mib: 128

  resource/environment:
    attributes:
      - key: deployment.environment.name
        value: staging
        action: insert

  # Identical to production. Redaction bugs must surface here, not in prod.
  attributes/drop_secrets:
    actions:
      - key: http.request.header.authorization
        action: delete
      - key: http.request.header.cookie
        action: delete
      - key: http.response.header.set_cookie
        action: delete
      - key: db.query.text
        action: delete
      - key: db.statement
        action: delete
      - key: user.email
        action: delete

  # Traces only. The logs pipeline must keep exception detail — it is the only
  # carrier the error contract leaves for it (`../conventions/errors.md`).
  attributes/drop_span_exception_detail:
    actions:
      - key: exception.message
        action: delete
      - key: exception.stacktrace
        action: delete

  batch:
    timeout: 5s
    send_batch_size: 512

exporters:
  otlphttp/traces:
    endpoint: ${env:TRACES_ENDPOINT}
    headers:
      Authorization: ${env:TRACES_AUTHORIZATION}
    sending_queue:
      enabled: true
      queue_size: 2000
    retry_on_failure:
      enabled: true
      initial_interval: 5s
      max_interval: 30s
      max_elapsed_time: 5m

  otlphttp/metrics:
    endpoint: ${env:METRICS_ENDPOINT}
    headers:
      Authorization: ${env:METRICS_AUTHORIZATION}

  otlphttp/logs:
    endpoint: ${env:LOGS_ENDPOINT}
    headers:
      Authorization: ${env:LOGS_AUTHORIZATION}

service:
  extensions: [health_check]
  telemetry:
    resource:
      attributes:
        - name: service.name
          value: otel-collector-gateway
        - name: deployment.environment.name
          value: staging
    # The platform log agent collects stderr. Do not feed these records back
    # through this Collector's own OTLP receiver.
    logs:
      level: info
      encoding: json
    metrics:
      level: normal
      readers:
        - periodic:
            timeout: 5000
            exporter:
              otlp:
                protocol: http/protobuf
                endpoint: ${env:SELF_METRICS_ENDPOINT}
                headers:
                  Authorization: ${env:SELF_METRICS_AUTHORIZATION}
  pipelines:
    traces:
      receivers: [otlp]
      # No tail_sampling: staging keeps everything.
      processors:
        - memory_limiter
        - resource/environment
        - attributes/drop_secrets
        - attributes/drop_span_exception_detail
        - batch
      exporters: [otlphttp/traces]

    metrics:
      receivers: [otlp]
      processors: [memory_limiter, resource/environment, attributes/drop_secrets, batch]
      exporters: [otlphttp/metrics]

    logs:
      receivers: [otlp]
      # Secrets go; exception detail stays. See the processor comment above.
      processors: [memory_limiter, resource/environment, attributes/drop_secrets, batch]
      exporters: [otlphttp/logs]
```

The one thing staging must share with production is **redaction**. A staging config without it means the first real test of the redaction rules happens in production with real user data.

Use separate backend credentials per environment, and keep environments visually separated on dashboards by `deployment.environment.name`.

### GenAI destination views are not sampling

"No unnecessary filtering" does not mean every trace backend must receive identical spans and
attributes. When a lower environment includes a GenAI backend, keep the same destination contract
as production while removing only retention sampling:

- the main trace backend receives the complete request/job trace with verbose GenAI payloads and
  neutral presentation copies removed;
- the GenAI backend receives the same trace ID as a rooted, ancestor-closed projection containing
  the entry root, GenAI spans, and their meaningful business ancestors;
- universal secret redaction applies to both branches, while approved captured GenAI context is
  retained only on the GenAI branch;
- no `tail_sampling` processor is present.

Use the marker and filter from `component.md`, and exercise them in development and staging so a
missing root or business ancestor is found before production. Do not replace this with a second
application provider or detached GenAI roots.

---

## Metrics are never sampled like traces

Even in production, metrics keep flowing at full fidelity. A sampled trace stream cannot produce accurate request counts, error rates, token totals, or SLO burn. There is no `tail_sampling` in any metrics pipeline on this page, and there should not be one in `production.md` either.

---

## Verify

Send one request through an instrumented service and confirm:

```bash
docker compose logs --tail=200 otel-collector | head -60
```

- the metrics backend contains application metrics such as `app.*`, `gen_ai.*`,
  or `http.server.*` from the canary;
- the monitoring destination contains this Collector's
  `otelcol_process_uptime`; receiver/export counters increase and
  `otelcol_exporter_send_failed_*` stays at zero;
- the debug exporter prints spans with your `service.name` and populated attributes;
- the backend can find `service.name=<your service>`.

Container logs alone are not proof of delivery. Look in the backend.
