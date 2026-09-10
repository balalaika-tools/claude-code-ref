# Documentation verification

Apply before delivering generated or updated documentation. Scale checks to the change; formatting validation alone cannot establish accuracy.

## Structural checks

- Every page intended for navigation is reachable from the documentation index; related procedures and references link to one another.
- Local page links, image targets, source references, and heading anchors resolve from the containing page. Check case sensitivity for Linux-hosted renderers even when working on a case-insensitive filesystem.
- Respect the existing renderer's link and anchor conventions. Prefer the project's docs build or link checker when available. If checked manually, describe it as manual review; do not claim a complete link crawl.
- New pages have descriptive titles, stable headings, and useful scope/source information. Remove scaffold placeholders and empty sections; retain explicitly explained unknowns and necessary example substitutions.
- Existing generated sections, navigation conventions, and authored material remain intact unless the requested update requires changing them.

## Factual consistency

Cross-check the index, architecture, service pages, and references for conflicting service names, ports, paths, defaults, environments, ownership, event identifiers, and state boundaries. Reopen sources for important operational claims rather than trusting prose generated earlier in the same task.

Check that commands exist, package-script targets resolve, CI job names match, working directories are correct, and documented prerequisites follow the implementation. State the evidence when source behavior and existing docs disagree.

Inspect the diff for accidental secrets, user-specific absolute paths, copied production records, unsupported claims, unrelated edits, and unnecessary whole-file rewrites.

## Command and build verification

Use existing Markdown/link/docs checks where available and permitted. Review command definitions before execution: even a build, test, or help command can invoke network access or mutate resources. Run appropriate local checks within the authorized scope. Do not install a new documentation toolchain solely to claim validation.

Do not deploy, apply infrastructure, modify remote state, run destructive migrations, replay live jobs, or exercise production systems merely to verify a guide. A documentation request authorizes documenting procedures; operational execution needs its own authorization.

For commands described in the docs, distinguish:

| Status | Meaning |
|---|---|
| Executed successfully | Run in the stated environment; record relevant result and limits |
| Checked against source | Command and prerequisites inspected, but runtime success not verified |
| Blocked | Could not verify because of a specific missing dependency, credential, or environment |
| Not applicable | Repository does not have this workflow, with a brief reason |

A successful local docs build does not verify deployment or recovery instructions. Record failed checks honestly and fix documentation defects where possible.

## New-engineer walkthrough

Using the manual as the entrypoint, follow links and procedures needed to answer each applicable question:

| Reader task | Evidence that coverage is useful |
|---|---|
| Understand the system | Purpose, boundaries, component/state ownership, and a traced flow |
| Find the implementation | Exact paths and representative entrypoints or extension points |
| Run locally | Prerequisites, configuration, setup/start commands, expected smoke result |
| Modify a component safely | Relevant contracts, state implications, representative change recipe |
| Run tests | Real commands, backing services/fixtures, expected outcomes |
| Release or deploy | Actual artifact and workflow, environment selection, verification |
| Observe behavior | Existing signals and a way to correlate a request or job |
| Diagnose a failure | Symptoms, evidence-backed checks, bounded recovery guidance |
| Roll back or recover | Supported mechanism and compatibility/data limits, or explicit missing knowledge |

Do not count a heading as coverage. If completing a procedure requires guessing an identifier, command, prerequisite, or outcome, fix it from evidence or record the missing knowledge. This is a desk walkthrough unless the workflows were actually executed; describe it accordingly.

## Gap reporting and handoff

Keep material unresolved gaps near the affected procedure, with a short index summary when several gaps block onboarding or operations. For each gap, identify the missing fact, sources inspected, practical impact, and next verification step. Do not create pages of repeated `Unknown` entries for irrelevant topics.

Report the entry path, coverage, checks and outcomes, and remaining limitations. If an important procedure is only source-reviewed, make that visible. Avoid “complete” or “production-ready” claims when deployment, recovery, or other applicable workflows remain unverified or undocumented.
