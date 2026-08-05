# AWS SSM Parameter Store Secrets Pattern

## Contents

- [Rule](#rule)
- [Terraform-Owned Write-Only Values](#terraform-owned-write-only-values)
- [Choose the Runtime Integration](#choose-the-runtime-integration)
- [Terraform Inputs](#terraform-inputs)
- [Least-Privilege IAM](#least-privilege-iam)
- [Application Runtime Fetch](#application-runtime-fetch)
- [Secret Lifecycle](#secret-lifecycle)

## Rule

Choose one writer for each parameter:

1. **Terraform-owned value:** Use `aws_ssm_parameter.value_wo` with
   `value_wo_version`, Terraform 1.11.0 or later, AWS provider 5.87.0 or later,
   and an ephemeral input path.
2. **Externally owned value:** Let the approved operator or CI secrets workflow
   create and rotate the parameter. Terraform manages only workload
   configuration, exact names/ARNs or a prefix, and least-privilege IAM.

Do not create or read secret values through ordinary Terraform arguments or data
sources when the requirement is to keep them out of state and plans. Store
sensitive values only as `SecureString`; never use `String` or `StringList` for
a secret.

Do not create a placeholder with `value` and then hide changes with
`ignore_changes`. For an externally owned value, do not declare the
`aws_ssm_parameter` resource merely to claim its metadata; the resource requires
a value. Pass its name, ARN, or hierarchy prefix instead.

## Terraform-Owned Write-Only Values

Write-only arguments let Terraform create and rotate a `SecureString` without
persisting the value in plan or state:

```hcl
terraform {
  required_version = ">= 1.11.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.87.0"
    }
  }
}

variable "runtime_secret_value" {
  description = "SecureString value supplied transiently by the approved secrets system"
  type        = string
  sensitive   = true
  ephemeral   = true
}

variable "runtime_secret_value_version" {
  description = "Non-secret revision; increment exactly once for each intended write"
  type        = number

  validation {
    condition = (
      var.runtime_secret_value_version >= 1 &&
      floor(var.runtime_secret_value_version) == var.runtime_secret_value_version
    )
    error_message = "runtime_secret_value_version must be a positive integer."
  }
}

variable "ssm_kms_key_arn" {
  description = "Optional customer-managed KMS key ARN for the SecureString"
  type        = string
  default     = null
}

resource "aws_ssm_parameter" "database_password" {
  name             = "/${var.project_name}/${var.environment_name}/database/password"
  description      = "Application database password"
  type             = "SecureString"
  key_id           = var.ssm_kms_key_arn
  value_wo         = var.runtime_secret_value
  value_wo_version = var.runtime_secret_value_version
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

Commit or otherwise review the non-secret version counter. Increment it whenever
the value must be written; changing the secret source without changing the
counter does not request an update. Terraform discards the value and cannot
compare it with the remote value, so it cannot detect secret-value drift. Do not
mix Terraform and out-of-band rotation without an explicit ownership handoff.

## Choose the Runtime Integration

Choose one pattern deliberately:

- **Application SDK fetch:** Pass a prefix or parameter names to the workload.
  Grant the task/function role access. Cache values and define refresh/failure
  behavior in the application. This supports controlled refresh without a new
  deployment.
- **ECS secret injection:** Put parameter ARNs in the task definition's
  `secrets` field. Grant the task execution role the required SSM/KMS access.
  The value is injected into the container environment at task start and
  refreshes only when a new task starts.
- **Lambda Parameters and Secrets extension:** Pass parameter names and let the
  extension retrieve/cache values at invocation time.

All three keep the value itself out of Terraform when configuration contains
only names or ARNs. Read
[`secrets-manager-pattern.md`](secrets-manager-pattern.md) when the selected
environment uses AWS Secrets Manager.

## Terraform Inputs

For application fetch by prefix:

```hcl
variable "aws_account_id" {
  description = "AWS account that owns the parameters"
  type        = string
}

variable "ssm_parameter_prefix" {
  description = "Environment/component prefix, for example /ai-exception/prod/db"
  type        = string

  validation {
    condition     = startswith(var.ssm_parameter_prefix, "/")
    error_message = "ssm_parameter_prefix must start with '/'."
  }
}
```

Inject only the non-secret prefix:

```hcl
environment = [
  {
    name  = "SSM_PARAMETER_PREFIX"
    value = var.ssm_parameter_prefix
  }
]
```

For ECS-native injection, store the ARN in `valueFrom`:

```hcl
secrets = [
  {
    name      = "DATABASE_PASSWORD"
    valueFrom = var.database_password_parameter_arn
  }
]
```

Do not use `data "aws_ssm_parameter"` with `with_decryption = true` for this
pattern; Terraform can persist the returned value.

## Least-Privilege IAM

For callers that fetch individual names:

```hcl
data "aws_iam_policy_document" "read_parameters" {
  statement {
    sid = "ReadApplicationParameters"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
    ]
    resources = [
      "arn:aws:ssm:${var.aws_region}:${var.aws_account_id}:parameter${var.ssm_parameter_prefix}/*"
    ]
  }
}
```

Add `ssm:GetParametersByPath` only when the application actually calls it.
Access to a parent path permits recursive retrieval below that path, so choose
the narrowest prefix the workload owns.

For a customer-managed KMS key, scope decryption to the key and SSM service:

```hcl
statement {
  sid       = "DecryptApplicationParameters"
  actions   = ["kms:Decrypt"]
  resources = [var.ssm_kms_key_arn]

  condition {
    test     = "StringEquals"
    variable = "kms:ViaService"
    values   = ["ssm.${var.aws_region}.amazonaws.com"]
  }

  condition {
    test     = "ArnLike"
    variable = "kms:EncryptionContext:PARAMETER_ARN"
    values = [
      "arn:aws:ssm:${var.aws_region}:${var.aws_account_id}:parameter${var.ssm_parameter_prefix}/*"
    ]
  }
}
```

Also configure the KMS key policy to authorize the workload principal. Verify
the exact encryption-context key used by the current SSM/KMS integration before
shipping the policy. The default AWS-managed SSM key has broader account-level
decrypt behavior; prefer a customer-managed key when isolation requirements
demand a narrower boundary.

## Application Runtime Fetch

Select the runtime provider from the non-secret prefix:

```python
def build_secrets_provider() -> SecretsProvider:
    prefix = os.environ.get("SSM_PARAMETER_PREFIX")
    if prefix:
        return SSMSecretsProvider(prefix=prefix)
    return EnvSecretsProvider()
```

Construct a normalized path and request decryption:

```python
name = f"{self._prefix.rstrip('/')}/{key.lstrip('/')}"
result = self._client.get_parameter(Name=name, WithDecryption=True)
```

Cache values to avoid an SSM API call on every request, but define how rotation,
expiration, throttling, and temporary SSM failures behave.

## Secret Lifecycle

For Terraform-owned write-only values, supply the ephemeral input and increment
`value_wo_version` through the reviewed deployment workflow before starting or
rolling the workload.

For externally owned values, write and rotate through one of:

- An operator bootstrap command or runbook.
- A CI/CD secrets deployment or rotation job.
- A dedicated secrets-management platform.

Use a consistent hierarchy:

```text
/{project}/{env}/{component}/{key}

/ai-exception/prod/database/password
/ai-exception/prod/payments/third-party-api-key
```

Never commit secret values to `.tfvars`, backend configuration, generated plan
JSON, CI logs, or Terraform state.
