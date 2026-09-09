# Errors, Privacy, and Redaction

## Failure record contract

The boundary that decides the operation's final outcome emits exactly one `error` record while its correlation context is active. Include:

- a stable failure event name;
- bounded `error.type`, normally the exception class or stable provider/domain code;
- a safe authored message or stable reason code;
- current execution and permitted business correlation;
- exception detail according to the central policy.

Do not use `str(exc)` as `error.type`, an event name, or a bounded field. Do not log and re-raise at every layer. Inner code may wrap with a meaningful domain exception and preserve the cause, but it should not emit another terminal record.

A failed attempt that is handled and later succeeds may emit one `warning` at the recovery boundary with `outcome=retried|fallback|degraded`, attempt, and bounded error type. The successful outer operation is not an error.

## Exception detail policy

Always add typed `LOG_FULL_EXCEPTION_TRACE`, default `true`, independently of environment and log level.

When true:

- render the complete exception cause chain once;
- place it in `exception.stacktrace`;
- do not enable local-variable capture;
- set `app.error.stacktrace_included=true`.

When false:

- remove the raw traceback and raw exception message;
- retain a safe authored message, bounded `error.type`, stable reason/code, and correlation;
- set `app.error.stacktrace_included=false`.

Call sites pass exception information to the central renderer and never branch on the policy. Redact credentials and tokens in both modes. Check the destination's record-size limit: truncate safely below it when necessary, mark `app.error.stacktrace_truncated=true`, and retain the rest of the record. Never let an oversized traceback cause the only failure record to disappear silently.

## Data classification

Default-deny these values:

```text
passwords, access/refresh tokens, API keys, session cookies
Authorization and Set-Cookie headers
private keys, connection strings, signed URLs
full request/response bodies and arbitrary message payloads
personal data, document contents, prompts and model outputs
```

Prefer allowlisting fields over chasing secret key names. When redaction is needed, traverse nested dictionaries, sequences, exception metadata, and rendered URLs; key-only top-level filters are insufficient. Use a stable marker such as `[REDACTED]`, never a reversible transform. Hashing personal identifiers still creates personal data and high-cardinality values; it requires policy approval and rotation rules.

Never capture process environment, local variables, object `repr`, or whole configuration objects. Treat user-controlled log fields as untrusted: prevent reserved-key overwrite and sanitize control characters that could forge multiline records.

## Correlation and privacy

Identifiers such as `user_id`, `tenant_id`, conversation ID, order ID, IP address, and request body fragments need a concrete search purpose plus suitable retention and access control. Prefer opaque business IDs over names or emails. Do not copy all incoming headers into context.

Record data-classification and retention assumptions in the completion report when the repository does not define them. Do not invent consent or authorization.

