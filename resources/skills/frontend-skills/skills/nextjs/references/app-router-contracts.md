---
title: Respect App Router Contracts
impact: HIGH
tags: app-router, file-conventions, async-apis, rsc, route-handlers, runtime
---

# App Router Contracts

Inspect the installed `next` version and the project's existing router before changing code. For Next.js 16 projects, prefer App Router patterns unless the project already uses the Pages Router; do not silently migrate routers as part of an unrelated task.

## Async request APIs

In Next.js 16, request-bound values are asynchronous. Await `params`, `searchParams`, `cookies()`, `headers()`, and `draftMode()` before reading them. The temporary synchronous compatibility from Next.js 15 is gone.

```tsx
export default async function Page(props: PageProps<'/products/[slug]'>) {
  const { slug } = await props.params
  const searchParams = await props.searchParams
  return <Product slug={slug} preview={searchParams.preview === '1'} />
}
```

Run `next typegen` when generated route helpers such as `PageProps`, `LayoutProps`, or `RouteContext` are unavailable.

## Server and Client Component boundaries

- Components are Server Components unless a file begins with `'use client'`.
- Keep the client boundary as low as practical; importing a module from a Client Component pulls that module into the client graph.
- Do not declare a Client Component as `async`. Fetch initial data in a Server Component or use an appropriate client data layer.
- Props crossing from server to client must be serializable. Functions may cross only through supported Server Function/Action contracts.
- Keep secrets, database access, and server-only modules outside the client graph.

## File-system ownership

Use the framework's special files for their intended boundaries: `layout`, `page`, `loading`, `error`, `not-found`, `route`, `default`, and metadata files. A `route.ts` and `page.tsx` cannot own the same route segment because each claims all HTTP verbs for that path. Put an API endpoint in a separate segment such as `app/api/.../route.ts`.

## Route Handlers

Route Handlers live under `app` and use the Web `Request` and `Response` APIs. Export only supported HTTP methods. Dynamic `params` are promises in Next.js 16 and can be typed with `RouteContext`.

Use a Route Handler for an HTTP endpoint consumed outside the React mutation flow, webhooks, callbacks, feeds, or protocol-specific responses. Prefer a Server Action for a mutation invoked directly by the app's React UI. Both are externally reachable server entry points and require their own validation and authorization.

## Runtime selection

Use the Node.js runtime by default. Opt into `export const runtime = 'edge'` only for a concrete deployment requirement and only after verifying that every dependency and Node API used by the route is Edge-compatible. Do not choose Edge merely because the route is short.

References: [Next.js 16 upgrade guide](https://nextjs.org/docs/app/guides/upgrading/version-16), [Route Handlers](https://nextjs.org/docs/app/getting-started/route-handlers), [Server and Client Components](https://nextjs.org/docs/app/getting-started/server-and-client-components), [Edge Runtime](https://nextjs.org/docs/pages/api-reference/edge)
