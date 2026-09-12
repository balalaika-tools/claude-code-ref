---
title: Debug Against the Running Application
impact: HIGH
tags: debugging, mcp, devtools, typegen, build, runtime
---

# Runtime Debugging

Use the installed framework version and live application state as the source of truth. Static guidance cannot reveal the current route tree, active errors, cache behavior, or browser hydration state.

## Fast inspection loop

1. Check the installed Next.js version and run `next info` when environment details matter.
2. Run `next typegen` after route changes when generated `PageProps`, `LayoutProps`, or `RouteContext` types are stale or missing.
3. Start the development server and reproduce the target route.
4. Read terminal, server, browser-console, network, and hydration errors before editing.
5. Make the smallest relevant change, then re-check the same runtime evidence.
6. Run a production build for changes involving prerendering, caching, server/client boundaries, or deployment behavior.

## Next.js DevTools MCP

For Next.js 16+, configure the documented `next-devtools-mcp` server when the active coding environment supports MCP. Use its runtime tools to discover the running server and inspect errors, logs, route metadata, project metadata, and Server Action locations. Do not hard-code the private `/_next/mcp` transport or assume a specific port when the supported MCP package can discover the server.

MCP diagnostics complement browser verification; they do not prove that interactions, visual states, or accessibility behavior work correctly.

## Targeted build diagnostics

- Use `next build --debug-prerender` for readable prerender stack traces. Do not deploy a build created with this debugging mode.
- Use `next build --debug-build-paths="app/**/page.tsx"` to narrow a large build while investigating specific routes.
- Use `next experimental-analyze` for Turbopack bundle analysis when bundle composition is the question.

With `npm run`, place `--` before Next CLI flags so npm forwards them to the framework command.

References: [Next.js MCP guide](https://nextjs.org/docs/app/guides/mcp), [Next.js CLI](https://nextjs.org/docs/app/api-reference/cli/next), [AI agents guide](https://nextjs.org/docs/app/guides/ai-agents)
