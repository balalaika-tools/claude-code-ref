---
title: Secure Every Server Entry Point
impact: CRITICAL
tags: security, authentication, authorization, server-actions, route-handlers, proxy
---

# Secure Every Server Entry Point

Treat Server Actions and Route Handlers as public-facing endpoints. A caller can invoke a Server Action with a direct POST request without using the rendered form or button, so hidden UI and client-side checks are never authorization controls.

For each server entry point:

1. Parse and validate all untrusted input on the server.
2. Verify the current session.
3. Authorize the specific resource and operation, not only the user's broad role.
4. Perform the mutation or read through a data-access boundary that repeats critical checks close to the data.
5. Return only the fields the caller needs; use DTOs or explicit projections for sensitive records.

```ts
'use server'

export async function updateProject(input: unknown) {
  const data = updateProjectSchema.parse(input)
  const session = await verifySession()

  if (!session) throw new Error('Unauthenticated')
  await assertCanEditProject(session.userId, data.projectId)

  return projects.update(data)
}
```

## Proxy is a prefilter

Use `proxy.ts` for coarse, optimistic redirects or request filtering when it improves UX. Do not make Proxy the only authorization layer: nested routes, Server Actions, and Route Handlers remain independently reachable, and prefetched requests also pass through Proxy. Repeat secure checks at the server entry point or data-access layer.

## Route Handler responses

Return `401` when no valid authentication is present and `403` when an authenticated caller lacks permission. Do not leak sensitive authorization details in the response body or logs.

## Shared server state

Never place request or user data in mutable module-level variables. Concurrent renders and requests may share the same process. Immutable configuration and deliberately keyed cross-request caches are different; request-scoped state is not.

References: [Next.js authentication guide](https://nextjs.org/docs/app/guides/authentication), [Data security](https://nextjs.org/docs/app/guides/data-security), [Server Actions security](https://nextjs.org/docs/app/getting-started/updating-data#security)
