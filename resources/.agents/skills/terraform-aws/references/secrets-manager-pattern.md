# AWS Secrets Manager Pattern

## Contents

- [Rule](#rule)
- [Model Secret Metadata in Terraform](#model-secret-metadata-in-terraform)
- [Terraform-Owned Write-Only Values](#terraform-owned-write-only-values)
- [Choose the Runtime Integration](#choose-the-runtime-integration)
- [Grant Least-Privilege Access](#grant-least-privilege-access)
- [Configure Rotation and Recovery](#configure-rotation-and-recovery)
- [Apply Production Guardrails](#apply-production-guardrails)
- [Migrate Between Stores](#migrate-between-stores)

## Rule

Choose one writer for each secret:

1. **Terraform-owned value:** Use
   `aws_secretsmanager_secret_version.secret_string_wo` with
   `secret_string_wo_version`, Terraform 1.11.0 or later, AWS provider 5.88.0
   or later, and an ephemeral input path.
2. **Externally owned value:** Populate and rotate versions through a controlled
   operator, CI secrets workflow, AWS managed-service integration, or rotation
   function. Terraform manages only the container and non-secret
   infrastructure.

Keep secret values out of ordinary Terraform arguments and data sources.
Terraform state and saved plans can retain any value that Terraform reads or
writes, even when an input or output is marked `sensitive`.

Let Terraform manage this non-secret infrastructure in either ownership model:

1. The `aws_secretsmanager_secret` container and its metadata.
2. A customer-managed KMS key and policy when the threat model requires one.
3. Rotation infrastructure and schedules that do not embed a secret value.
4. The workload configuration that points to explicit secret ARNs.
5. Least-privilege IAM and optional VPC endpoints.

Do not create `aws_secretsmanager_secret_version` with ordinary `secret_string`
or `secret_binary` merely to bootstrap a value; that places the value in state.
Do not read a version with a Terraform data source for runtime injection.

## Model Secret Metadata in Terraform

Create the recoverable secret container without a value:

```hcl
variable "secret_kms_key_arn" {
  description = "Optional customer-managed KMS key ARN for runtime secrets"
  type        = string
  default     = null
}

resource "aws_secretsmanager_secret" "database" {
  name                    = "/${var.project_name}/${var.environment_name}/database/app"
  description             = "Application database credential"
  kms_key_id              = var.secret_kms_key_arn
  recovery_window_in_days = 30
}

output "database_secret_arn" {
  description = "ARN used by the workload to retrieve the database credential"
  value       = aws_secretsmanager_secret.database.arn
}
```

Keep names, descriptions, and tags non-sensitive because Secrets Manager does
not encrypt that metadata. Use a customer-managed symmetric KMS key when
cross-account access, compliance, or tighter separation requires it; otherwise
evaluate whether the AWS managed key is sufficient. Apply rotation and workload
key permissions in both IAM and the KMS key policy.

Store one independently rotated and authorized credential per secret. A JSON
object is appropriate when its fields must rotate together and have identical
read access, such as a username/password pair. Do not bundle unrelated secrets
to reduce the secret count; that widens IAM access and couples rotation.

Prefer an explicit ARN input when another stack or team owns the secret.
Do not discover secrets with broad name or tag searches. Avoid
`force_delete_without_recovery`; use a reviewed recovery window, normally 7–30
days. Consider `prevent_destroy` for durable production secret containers only
with an explicit break-glass removal procedure, and remember that it does not
protect a resource after its block is removed.

## Terraform-Owned Write-Only Values

Write-only arguments let Terraform create a secret version without persisting
the value in plan or state:

```hcl
terraform {
  required_version = ">= 1.11.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.88.0"
    }
  }
}

variable "runtime_secret_value" {
  description = "Secret value supplied transiently by the approved secrets system"
  type        = string
  sensitive   = true
  ephemeral   = true
}

variable "runtime_secret_value_version" {
  description = "Non-secret revision; increment exactly once for each intended secret version"
  type        = number

  validation {
    condition = (
      var.runtime_secret_value_version >= 1 &&
      floor(var.runtime_secret_value_version) == var.runtime_secret_value_version
    )
    error_message = "runtime_secret_value_version must be a positive integer."
  }
}

resource "aws_secretsmanager_secret_version" "database" {
  secret_id                = aws_secretsmanager_secret.database.id
  secret_string_wo         = var.runtime_secret_value
  secret_string_wo_version = var.runtime_secret_value_version
}
```

Supply `runtime_secret_value` transiently from an approved secret-delivery
system. Never put it in committed tfvars, command-line arguments, generated
files, logs, or a non-ephemeral downstream value. Write-only arguments accept
ordinary values, but an ordinary source merely relocates the leak.

For a saved-plan workflow, inject the root ephemeral variable again during
apply, for example through the same protected `TF_VAR_runtime_secret_value`
channel. Terraform permits the apply value to differ because it was not stored
in the plan, so pin the approved secret revision across both phases.

Increment the non-secret version counter whenever Terraform must create a new
secret version. Changing the source without changing the counter does not
request an update. Terraform discards the value and cannot compare it with the
remote value, so it cannot detect secret-value drift. Do not combine this
pattern with an out-of-band writer or managed rotation under competing
ownership; use the external-value path instead.

## Choose the Runtime Integration

Choose one pattern deliberately:

- **Application SDK fetch:** Pass the complete secret ARN to the application.
  Grant its workload role access, cache the value, and define refresh,
  throttling, stale-cache, and failure behavior. Prefer AWS-supported caching
  components where they fit.
- **ECS secret injection:** Put the complete ARN in the container definition's
  `secrets[].valueFrom`. Grant the task **execution role** access. Injected
  values update only when a new task starts, so coordinate rotation with a
  deployment or forced rollout.
- **Lambda Parameters and Secrets extension:** Pass the ARN and let the
  extension retrieve and cache the value at invocation time.
- **AWS managed-service integration:** Prefer a service-managed secret and
  managed rotation where the target service supports it, for example an RDS
  credential, instead of building a custom rotator by default.

For SDK retrieval in ECS, grant the task role rather than the execution role.
Never put secret values in ordinary task-definition environment entries,
Lambda environment variables, user data, command-line arguments, logs, or
Terraform outputs.

## Grant Least-Privilege Access

Pass complete ARNs and scope reads to the exact secrets:

```hcl
variable "runtime_secret_arns" {
  description = "Exact Secrets Manager ARNs the workload may read"
  type        = set(string)
}

data "aws_iam_policy_document" "read_runtime_secrets" {
  statement {
    sid       = "ReadRuntimeSecrets"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = var.runtime_secret_arns
  }
}
```

Add `secretsmanager:DescribeSecret`, `BatchGetSecretValue`, or `ListSecrets`
only when the runtime actually calls them. Do not use `Resource = "*"` for
`GetSecretValue`.

When a customer-managed KMS key protects the secrets, add `kms:Decrypt` scoped
to that key and constrain its use to Secrets Manager:

```hcl
statement {
  sid       = "DecryptRuntimeSecrets"
  actions   = ["kms:Decrypt"]
  resources = [var.secret_kms_key_arn]

  condition {
    test     = "StringEquals"
    variable = "kms:ViaService"
    values   = ["secretsmanager.${var.aws_region}.amazonaws.com"]
  }

  condition {
    test     = "ArnEquals"
    variable = "kms:EncryptionContext:SecretARN"
    values   = var.runtime_secret_arns
  }
}
```

Authorize the principal in the KMS key policy as well. For cross-account reads,
use the complete secret ARN, a narrowly scoped secret resource policy, identity
policy permission in the caller account, and a customer-managed KMS key that
authorizes the caller. Add a resource policy only when it is needed; for any
policy-writing path, enable public-policy blocking and validate that the policy
does not grant broad access.

## Configure Rotation and Recovery

Enabling an AWS-managed or Lambda rotation schedule makes that workflow the
value writer; do not also drive `secret_string_wo_version` for the same secret.
For externally managed values, define the rotation requirement before enabling
a schedule:

1. Prefer managed rotation when the AWS service supports it.
2. For custom rotation, give the Lambda role access only to the target secret,
   its KMS key, and the target service or database.
3. Ensure the function can reach both Secrets Manager and the rotated system.
4. Test the complete create, set, test, and finish sequence, including rollback
   and overlapping invocation behavior.
5. Monitor rotation failures and keep the `AWSCURRENT`/`AWSPREVIOUS` staging
   behavior compatible with the consumer.

Choose a schedule from the credential's exposure and operational requirements,
not from an arbitrary universal interval. Test rotation and consumer refresh in
a non-production environment before enabling production rotation.

Use the deletion recovery window for accidental-deletion protection. Before
retiring a secret, remove consumers and access, wait through the agreed
observation period, then schedule deletion. Do not force immediate deletion in
normal workflows.

## Apply Production Guardrails

- Use CloudTrail, CloudWatch alarms, AWS Config, and the organization's threat
  detection controls to monitor access, policy changes, deletion, and rotation
  failures without logging values.
- Use a Secrets Manager interface VPC endpoint when private-network policy or
  egress design requires it. Test service integrations before enforcing
  `aws:SourceVpc` or `aws:SourceVpce`, because overly broad deny conditions can
  break rotation and AWS service access.
- Restrict who can call `PutSecretValue`, change rotation, attach resource
  policies, alter the KMS key, or schedule deletion. Separate read, write,
  rotation, and administration roles.
- Avoid exposing secret material through CLI history, shell tracing, temporary
  files, CI output, crash reports, or application telemetry.
- Plan and test regional replication, failover, and rotation behavior when
  disaster recovery requires replicas.

## Migrate Between Stores

Treat SSM-to-Secrets-Manager and Secrets-Manager-to-SSM changes as secret
migrations, not Terraform resource renames:

1. Create the destination metadata and least-privilege IAM.
2. Copy the value through the approved secrets workflow, never through
   Terraform.
3. Verify retrieval and rotation in the destination.
4. Deploy consumers with the new store identifier and ARN/name.
5. Observe the cutover, revoke source access, and retire the source through its
   recovery process.

Never use a Terraform `moved` block between SSM and Secrets Manager resources;
they are different remote object types with different lifecycle semantics.
