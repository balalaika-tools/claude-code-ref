# SSM Secrets Pattern

## The rule

Terraform **never** creates or manages the secret values in SSM Parameter Store. It only:

1. Accepts the SSM prefix as an input variable (e.g. `ssm_parameter_prefix = "/ai-exception/prod"`).
2. Injects that prefix as an environment variable (`SSM_PARAMETER_PREFIX`) into the ECS task definition or Lambda.
3. Grants the task/function IAM permission to read parameters under that prefix.

The application code then constructs full SSM paths at runtime using the prefix.

## Why

Putting secret values in Terraform would persist them in state and plan files — even `sensitive = true` only hides values from CLI output. The prefix approach means state contains no secret material at all.

## Terraform side

### Variable (module or environment)

```hcl
variable "ssm_parameter_prefix" {
  description = "Environment-root SSM prefix, e.g. /ai-exception/prod"
  type        = string
}
```

### Environment variable injected into the container/function

```hcl
environment {
  variables = {
    SSM_PARAMETER_PREFIX = var.ssm_parameter_prefix
  }
}
```

### IAM: scope the read permission to the prefix subtree

```hcl
{
  Sid    = "ReadSSMSecrets"
  Effect = "Allow"
  Action = ["ssm:GetParameter", "ssm:GetParameters"]
  Resource = "arn:aws:ssm:${var.aws_region}:*:parameter${var.ssm_parameter_prefix}/*"
}
```

Add a `DecryptSSMSecureString` statement if secrets are stored as `SecureString`:

```hcl
{
  Sid      = "DecryptSSMSecureString"
  Effect   = "Allow"
  Action   = ["kms:Decrypt"]
  Resource = "<kms-key-arn>"
}
```

## Application side

The app detects whether `SSM_PARAMETER_PREFIX` is set and switches providers:

```python
def build_secrets_provider() -> SecretsProvider:
    prefix = os.environ.get("SSM_PARAMETER_PREFIX")
    if prefix:
        return SSMSecretsProvider(prefix=prefix)  # prod
    return EnvSecretsProvider()                    # local dev (.env)
```

`SSMSecretsProvider` builds the full parameter name by appending logical keys to the prefix:

```python
# prefix = "/ai-exception/prod"
# key    = "db/password"
# → fetches /ai-exception/prod/db/password
name = f"{self._prefix}/{key.strip('/')}"
result = self._client.get_parameter(Name=name, WithDecryption=True)
```

## Secret lifecycle (outside Terraform)

The actual parameter values must be written to SSM **before** the service starts, through a separate process — typically:

- Manual `aws ssm put-parameter` during initial environment bootstrap.
- A CI/CD secrets-rotation job.
- An operator runbook.

Never run `aws_ssm_parameter` Terraform resources for secrets whose values you want to keep out of state.

## Naming convention

```
/{project}/{env}/{component}/{key}

/ai-exception/prod/db/password
/ai-exception/prod/third-party/api-key
```

Pass the environment-root prefix (`/ai-exception/prod`) when the app owns all paths beneath it, or a narrower prefix (`/ai-exception/prod/db`) when you want to scope IAM to just one subsystem.
