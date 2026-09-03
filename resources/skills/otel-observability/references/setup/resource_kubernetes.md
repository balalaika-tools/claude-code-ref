# Kubernetes Resource Identity

Read this file only when the service runs in Kubernetes. Read
`resource_processes.md` as well when one Pod or container runs multiple
telemetry-producing processes.

For the common one-application-process-per-Pod model, use the Pod UID as
`service.instance.id`. Inject it through the Downward API rather than parsing
the pod name:

```yaml
env:
  - name: POD_UID
    valueFrom:
      fieldRef:
        fieldPath: metadata.uid
  - name: POD_NAME
    valueFrom:
      fieldRef:
        fieldPath: metadata.name
  - name: POD_NAMESPACE
    valueFrom:
      fieldRef:
        fieldPath: metadata.namespace
  - name: SERVICE_INSTANCE_ID
    valueFrom:
      fieldRef:
        fieldPath: metadata.uid
```

Also preserve `k8s.pod.uid`, `k8s.pod.name`, `k8s.namespace.name`, and
`k8s.container.name` through application resource detection or the Collector's
Kubernetes attributes processor.

Pod UID alone is not sufficient when multiple containers or processes emit
telemetry with the same `service.namespace` and `service.name`. In that case,
derive the instance ID from Pod UID plus container identity, or generate one
UUID per process. Record the source identities under their native attributes.

The OpenTelemetry Kubernetes recommendation also permits an explicit
`resource.opentelemetry.io/service.instance.id` pod annotation and otherwise
derives the value from namespace, pod, and container names. Follow that rule
when an existing Kubernetes observability stack already owns service-attribute
derivation; do not add a competing application rule. See the
[Kubernetes service-attribute calculation](https://opentelemetry.io/docs/specs/semconv/non-normative/k8s-attributes/).

Failure signal: if every replica has the same ID, a deployment ordinal,
service name, or UUID created before a worker fork owns the attribute.

---

## Then

- back to `resource_identity.md` if any ownership question is still open;
- multiple telemetry-producing processes in one container: `resource_processes.md`;
- then continue with `sdk_bootstrap.md`.
