# Pre-Fork Server Startup

Read this file in addition to the framework startup reference when Gunicorn,
uWSGI, or another pre-fork server owns the worker processes.

Initialize the OpenTelemetry SDK **in each worker after the fork** using the
server's post-fork hook. Exporter threads created in the parent do not survive
into children, and a process UUID generated in the parent would incorrectly
give every worker the same `service.instance.id`.

The post-fork hook must perform the complete per-process sequence:

```text
fork worker
  -> resolve per-process service.instance.id
  -> configure providers and exporters
  -> install process-wide instrumentation
  -> construct long-lived clients
  -> serve traffic
```

Shut down providers from the worker, not from the pre-fork parent. Verify two
workers export distinct instance IDs and both export spans under load.
