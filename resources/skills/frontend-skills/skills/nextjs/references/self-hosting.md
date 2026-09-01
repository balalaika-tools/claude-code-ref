---
title: Design Self-Hosting for the Actual Topology
impact: HIGH
tags: deployment, docker, standalone, cache, multi-instance, rolling-deploy
---

# Self-Hosting

Put a reverse proxy in front of a self-hosted Next.js server to handle malformed requests, slow connections, payload limits, and other concerns that should not reach the application process directly.

## Standalone output

For containers, `output: 'standalone'` creates a minimal `.next/standalone` server with traced production dependencies:

```ts
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  output: 'standalone',
}

export default nextConfig
```

The standalone output does not copy `public` or `.next/static` automatically. Serve them from a CDN or copy them into the corresponding standalone directories as part of the image build. In a monorepo, verify `outputFileTracingRoot` and any tracing includes instead of assuming files outside the app directory were captured.

## Single instance versus multiple instances

A single `next start` process with persistent local disk can use the default local cache. Multiple containers, ephemeral disks, or rolling deployments need explicit coordination:

- Use a shared cache design appropriate to the enabled cache model. `cacheHandler` configures the framework cache; `cacheHandlers` configures storage for `use cache` variants.
- Coordinate tag invalidation across instances; a custom handler may need `refreshTags()` so every instance observes revalidation.
- Use the same `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY` for instances serving the same build.
- Configure a stable `deploymentId` for version-skew protection during rolling deployments.
- Start every instance from the same build artifact. Do not rebuild independently per replica.

Cache Components and streaming work when self-hosted, but a proxy or CDN must not buffer streaming responses or override framework cache headers incorrectly.

## Environment variables

Treat `NEXT_PUBLIC_*` values as build-time public constants because they are inlined into browser bundles. Keep secrets server-only. If an SDK cannot initialize safely while modules are evaluated during `next build`, initialize it lazily at runtime rather than at module scope.

References: [Self-hosting](https://nextjs.org/docs/app/guides/self-hosting), [Standalone output](https://nextjs.org/docs/app/api-reference/config/next-config-js/output), [Deployment ID](https://nextjs.org/docs/app/api-reference/config/next-config-js/deploymentId), [Environment variables](https://nextjs.org/docs/app/guides/environment-variables)
