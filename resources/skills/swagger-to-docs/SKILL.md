---
name: swagger-to-docs
description: Converts a Swagger 2.0 JSON API specification into a single human-readable Markdown document (overview, services list, endpoints grouped by tag with parameter/response tables, and a data-model appendix). Use when the user asks to document, summarize, or make readable a swagger.json/openapi.json file, or to regenerate existing generated API docs after the spec changes.
---

# Swagger → Markdown API Documentation

Turns a Swagger 2.0 JSON spec into readable Markdown by running a `jq` filter over
it — no need to read the whole (often multi-thousand-line) JSON file by hand or
transcribe endpoints manually.

## Quick start

```bash
.claude/skills/swagger-to-docs/scripts/generate-api-docs.sh <input-swagger.json> [output.md]
```

- `output.md` defaults to `./<input-basename>-Documentation.md` if omitted.
- The script prints the endpoint and data-model counts it wrote — use these to
  sanity-check against `jq '[.paths[] | keys[]] | length' <input.json>` and
  `jq '.definitions | keys | length' <input.json>` if something looks off.

Example, run from the repo root:

```bash
.claude/skills/swagger-to-docs/scripts/generate-api-docs.sh documents/ctc-api-docs.json documents/CTC-API-Documentation.md
```

## What the output contains

1. **Header** — title, description, host, base path, version, contact, pulled from `.info`/`.host`/`.basePath`.
2. **Services Overview** — every Swagger `tag` and its description.
3. **Endpoints** — every operation grouped by its first tag, each with method, path, summary, description, a parameters table (name/in/required/type), and a responses table (code/description/schema). Array and `$ref` schema types are resolved to `array<TypeName>` / `TypeName` rather than left as raw JSON pointers.
4. **Data Models** — every entry in `.definitions`, alphabetized, with top-level property names and resolved types.

## When the input isn't Swagger 2.0

The script checks `.swagger` (or `.openapi`) and warns if the doc looks like
OpenAPI 3.x, since that format moves request bodies to `requestBody` and
schemas to `components/schemas` instead of `definitions` — the current filter
will produce a mostly-empty doc in that case. Do not try to run this script
against OpenAPI 3.x specs; instead adapt `scripts/swagger-to-md.jq`:
- point `dataModelsSection` at `.components.schemas` instead of `.definitions`
- add request-body extraction from `.requestBody.content["application/json"].schema` in `endpointEntry`

## Regenerating after the source spec changes

Just re-run the same command — it's fully deterministic and overwrites the
output file. Consider wiring this into a pre-commit hook or CI step if the
Swagger source lives in this repo and changes often, so the Markdown doc never
drifts out of sync.

## Customizing the output

The Markdown structure lives entirely in `scripts/swagger-to-md.jq`, organized
as small composable functions (`header`, `servicesOverview`, `endpointsSection`,
`dataModelsSection`). Edit that file directly for structural changes (e.g.
adding a table of contents with anchor links, filtering to specific tags, or
changing table columns) — don't hand-edit the generated Markdown, since it will
be overwritten on the next run.
