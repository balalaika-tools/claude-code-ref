# Amazon ECS Resource Identity

Read this file only when the service runs on Amazon ECS or Fargate. Read
`resource_processes.md` as well when one application container runs several
telemetry-producing processes.

## Contents

- [Identity choice](#identity-choice)
- [Metadata v4 contract](#metadata-v4-contract)
- [Startup resolver](#startup-resolver)
- [Mock metadata and expected mapping](#mock-metadata-and-expected-mapping)
- [Collector ownership](#collector-ownership)

## Identity choice

Choose the source at the granularity of the service instance:

| Runtime shape | `service.instance.id` source |
| --- | --- |
| One application container/process per task | `TaskARN` |
| Multiple same-service containers in one task | `ContainerARN` or `DockerId` |
| Multiple same-service processes in one container | one generated UUID per process |

Also retain the detected native attributes when available:

```text
cloud.provider=aws
cloud.platform=aws_ecs
aws.ecs.cluster.arn=...
aws.ecs.task.arn=...
aws.ecs.task.id=...
aws.ecs.container.arn=...
container.id=...
```

## Metadata v4 contract

ECS injects `ECS_CONTAINER_METADATA_URI_V4` into each container. Query the base
URI for the current container and `${ECS_CONTAINER_METADATA_URI_V4}/task` for
task metadata exactly once during startup, before constructing the immutable
OpenTelemetry `Resource`. Do not call either endpoint per request or span.

The v4 response may gain fields over time, so parse only the allowlisted keys
you use and ignore unknown keys. Do not use `/taskWithTags` for identity: it
makes ECS API calls, needs `ecs:ListTagsForResource`, and repeated calls can be
throttled. The endpoint and response contracts are documented by AWS:

- [metadata v4 paths](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-metadata-endpoint-v4.html)
- [metadata v4 response](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-metadata-endpoint-v4-response.html)
- [metadata v4 examples](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-metadata-endpoint-v4-examples.html)

`ContainerARN` is not present on older ECS Linux agents; fall back to
`DockerId` only for container-scoped identity. Fail startup if the chosen scope
has no valid source rather than silently assigning a shared service name.

## Startup resolver

Pass the injected metadata URI through the service's typed startup settings or
runtime adapter. `instance_scope` is a deployment decision; do not infer it
from the number of containers because sidecars do not necessarily represent
the same logical service.

<!-- complete-python-template -->
```python
from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Literal
from urllib.request import Request, urlopen


def _read_metadata(url: str) -> Mapping[str, object]:
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=1.0) as response:  # nosec: trusted ECS URI
        payload = json.load(response)
    if not isinstance(payload, Mapping):
        raise RuntimeError("ECS metadata response must be a JSON object")
    return payload


def ecs_resource_attributes(
    metadata_uri: str,
    *,
    instance_scope: Literal["task", "container"],
) -> dict[str, str]:
    container = _read_metadata(metadata_uri)
    task = _read_metadata(f"{metadata_uri.rstrip('/')}/task")

    task_arn = task.get("TaskARN")
    container_arn = container.get("ContainerARN")
    docker_id = container.get("DockerId")
    cluster = task.get("Cluster")

    if not isinstance(task_arn, str) or not task_arn:
        raise RuntimeError("ECS task metadata is missing TaskARN")

    if instance_scope == "task":
        instance_id = task_arn
    elif instance_scope == "container":
        if isinstance(container_arn, str) and container_arn:
            instance_id = container_arn
        elif isinstance(docker_id, str) and docker_id:
            instance_id = docker_id
        else:
            raise RuntimeError(
                "ECS container metadata has no ContainerARN or DockerId"
            )
    else:
        raise ValueError(f"unsupported ECS instance scope: {instance_scope}")

    attributes = {
        "service.instance.id": instance_id,
        "cloud.provider": "aws",
        "cloud.platform": "aws_ecs",
        "aws.ecs.task.arn": task_arn,
        "aws.ecs.task.id": task_arn.rsplit("/", 1)[-1],
    }
    if isinstance(cluster, str) and cluster.startswith("arn:"):
        attributes["aws.ecs.cluster.arn"] = cluster
    if isinstance(container_arn, str) and container_arn:
        attributes["aws.ecs.container.arn"] = container_arn
    if isinstance(docker_id, str) and docker_id:
        attributes["container.id"] = docker_id
    return attributes
```

## Mock metadata and expected mapping

Use fixtures shaped like the actual two v4 responses. Keep them minimal so
tests fail when the resolver starts depending on unrelated metadata:

```python
CONTAINER_V4 = {
    "DockerId": "ee08638adaaf009d78c248913f629e38299471d45fe7dc944d1039077e3424ca",
    "Name": "pricing-worker",
    "ContainerARN": "arn:aws:ecs:eu-west-1:111122223333:container/cluster/abc123",
}

TASK_V4 = {
    "Cluster": "arn:aws:ecs:eu-west-1:111122223333:cluster/pricing",
    "TaskARN": "arn:aws:ecs:eu-west-1:111122223333:task/pricing/158d1c8083dd49d6b527399fd6414f5c",
    "Family": "pricing-worker",
    "Revision": "26",
    "LaunchType": "FARGATE",
    "Containers": [CONTAINER_V4],
}
```

Expected task-scoped mapping:

```text
service.instance.id = arn:aws:ecs:eu-west-1:111122223333:task/pricing/158d1c8083dd49d6b527399fd6414f5c
aws.ecs.task.id      = 158d1c8083dd49d6b527399fd6414f5c
container.id         = ee08638adaaf009d78c248913f629e38299471d45fe7dc944d1039077e3424ca
```

Mock both requests in unit tests and assert that `instance_scope="container"`
selects `ContainerARN`, then remove `ContainerARN` from the fixture and assert
the documented `DockerId` fallback. Also assert that a missing `TaskARN` fails.

## Collector ownership

An ECS resource detector supplies native metadata; do not assume it also
chooses the service-level `service.instance.id`. A Collector-side ECS detector
is valid only when the Collector is in the same task and processes telemetry
for that task. A central ECS gateway would detect itself and must not overwrite
application resource identity.

---

## Then

- back to `resource_identity.md` if any ownership question is still open;
- a pre-fork server in the task also needs `resource_processes.md`;
- then continue with `sdk_bootstrap.md`.
