# Multi-Process Resource Identity

Read this file in addition to the selected platform reference when a pre-fork
server or worker pool creates several telemetry-producing processes in one
container.

Container, Pod, or task identity is not enough when multiple processes share
the same logical `service.namespace` and `service.name`. Generate a UUID per
child process after the fork and build the provider in that child. Do not
create one UUID in the parent and inherit it across workers.

When no platform identity is safely available, a UUID v4 created once at
process startup is the correct fallback. Keep it unchanged for that process's
lifetime; never generate it per request, span, or export batch.

For a uniform opaque representation, a platform identity may be converted to
UUID v5 while the original stays in its native platform attribute. The OTel
service convention defines the UUID namespace
`4d63009a-8d0f-11ee-aad7-4c796ed8e320` for this purpose.

Verify two child processes produce distinct `service.instance.id` values and
that neither value was created in the pre-fork parent.

---

## Then

- the container platform's own identity file, if one applies;
- pre-fork startup ordering: `startup_prefork.md`;
- then continue with `sdk_bootstrap.md`.
