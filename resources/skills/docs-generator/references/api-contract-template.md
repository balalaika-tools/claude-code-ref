# API contract page template

Use when writing a canonical API contract page (typically `reference/api.md`, or one page per independently versioned API) for a service with authenticated HTTP endpoints, aimed at testers and integrators as the definitive contract. The shape below is a starting point, not a form to fill in mechanically: adapt it to the actual API, omit sections it doesn't need, and add sections it does. A simple synchronous CRUD API may need only sections 1–4 and 7.

## Shape

1. **Title and one-line purpose.** What the API is for and who consumes it.
2. **Authentication.** Required configuration/environment values, one concrete token-acquisition request and response, and a table mapping scopes/roles to what they allow. Show the exact header format used on business requests (e.g. `Authorization: Bearer <token>`).
3. **Endpoint overview table.** Method, path, required scope/auth, and a one-line result, for every endpoint including health/readiness. This is the page's map; each per-endpoint section below expands one row.
4. **Per-endpoint sections**, one per endpoint or tight endpoint group, each with:
   - The exact request shape, including which fields are mutually exclusive, required, defaulted, or capped — grounded in the actual validator/schema, not inferred from field names.
   - One concrete example request and response (real shapes with placeholder values, not abbreviated pseudo-JSON).
   - What the response does and does not prove (e.g. a `202` proves durable admission, not that downstream work happened). This sentence is usually the most valuable one on the page and the easiest to omit by accident.
   - Idempotency/retry/dedup behavior: what happens on a repeated identical call, and whether any request header actually affects it.
5. **Result/state reference**, if the API exposes a state machine or enumerated statuses (state, status, assessment, confidence, cause, etc.): one table listing every value and its meaning, kept next to — not duplicated across — the endpoints that return it.
6. **Pagination**, if any endpoint returns pages: parameter names, defaults, maximums, cursor semantics, and which cursors are interchangeable across endpoints.
7. **Errors.** An HTTP-status table describing what each status means for this API specifically (not the generic RFC meaning), plus a table of domain-specific error/validation codes the caller should branch on.
8. **Checklist for the consumer**, when the API has real operational hazards: irreversible side effects, required polling-to-completion, fields that must be independently verified rather than trusted from the response, and any load/rate caveats not yet validated. Skip it when the API has no such hazards — it is not a generic reminder list.

## What makes this useful instead of decorative

- Ground every rule and default in the actual validator, router, or schema; cite it near the claim per this skill's sourcing rules, not only in an end-of-page reference list.
- State what a status code or field does *not* guarantee whenever that's easy to assume wrong (delivery, persistence, downstream completion) — usually more valuable to a tester than restating the schema.
- Keep one example per endpoint, not one exhaustive example per field combination; use the request-shape rules for the combinations.
- Sections 5–8 are conditional on the API actually having that behavior. Adding them to a simple API that has no state machine, no pagination, and no destructive side effects turns the template into padding.
