# Documentation verification

Apply before delivering generated or updated documentation. Scale checks to the change; formatting validation alone cannot establish accuracy.

## Structural checks

- Every page intended for navigation is reachable from the documentation index; related procedures and references link to one another.
- Local page links, image targets, source references, and heading anchors resolve from the containing page. Check case sensitivity for Linux-hosted renderers even when working on a case-insensitive filesystem.
- Respect the existing renderer's link and anchor conventions. Prefer the project's docs build or link checker when available. If checked manually, describe it as manual review; do not claim a complete link crawl.
- New pages start with descriptive titles and useful content, not repeated provenance blocks. Source links are contextual or in a short end-of-page reference section. Remove scaffold placeholders and empty sections; retain explicitly explained unknowns and necessary example substitutions.
- Existing generated sections, navigation conventions, and authored material remain intact unless the requested update requires changing them.

## Coverage gates

- Compare with the agreed structure and applicable reader tasks; an example blueprint does not make deployment, authentication, telemetry or any other absent feature mandatory. After a clean rebuild, no competing authentication/deployment procedures or orphaned legacy pages remain in scope.
- Where supported, walk first deployment, redeployment, fresh-terminal credential reuse, local readiness and a complete smoke separately. Check dependency order and test data; identity creation must not be required for each test.
- Reconcile configuration against all public fields/aliases, selectors, secret-provider inputs and applicable deployment inputs. Distinguish defaults, environment values and unused/unwired knobs.
- Reconcile inbound routes and outbound operations against contracts, including failure/async/write semantics.
- Reconcile metrics, important span/log call sites and configured export pipelines against observability documentation.

- Check README roles: the root has a clear summary, accurate shallow repository tree and documentation entry; the docs index provides complete task navigation without duplicating the root overview. A small repository may need only one index.
- Keep generation history, source-revision audit notes, check totals and test outcomes out of permanent pages. `Known gaps` contains only material unresolved inputs or defects, their practical impact and a link to the affected workflow.

## Factual consistency

Cross-check the index, architecture, service pages, and references for conflicting service names, ports, paths, defaults, environments, ownership, event identifiers, and state boundaries. Reopen sources for important operational claims rather than trusting prose generated earlier in the same task.

Check that commands exist, package-script targets resolve, CI job names match, working directories are correct, and documented prerequisites follow the implementation. State the evidence when source behavior and existing docs disagree.

Inspect the diff for accidental secrets, user-specific absolute paths, copied production records, unsupported claims, unrelated edits, and unnecessary whole-file rewrites.

## Command and build verification

Use existing Markdown/link/docs checks where available and permitted. Review command definitions before execution: even a build, test, or help command can invoke network access or mutate resources. Run appropriate local checks within the authorized scope. Do not install a new documentation toolchain solely to claim validation.

Do not deploy, apply infrastructure, modify remote state, run destructive migrations, replay live jobs, or exercise production systems merely to verify a guide. A documentation request authorizes documenting procedures; operational execution needs its own authorization.

Extract executable shell blocks and check zsh syntax where available, individually and as sequential procedures where appropriate. Review variable dependencies, interactive reads, quoting, reserved names, command existence and failure/timeout handling. Syntax checks must not execute embedded substitutions or cloud operations. Record syntax checks separately from execution: `zsh -n` does not verify flags, credentials or runtime success.

Track the following command-verification statuses in working notes and the final handoff/PR; do not render this audit table or repeat its statuses at the top of every page:

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

Keep concrete unresolved gaps near the affected procedure, with a short `Known gaps` index summary only when they materially affect applicable reader tasks. State what is missing or broken, its practical impact and the next action; link to source evidence where useful. Keep investigation history and lists of places searched in working notes. Do not list irrelevant topics, deliberate configuration choices or generic “not executed during generation” disclaimers as gaps.

In the final handoff or PR, report the entry path, coverage, checks and outcomes, source revision when useful, and remaining limitations. Distinguish source review from runtime execution there. In the manual, retain only procedure-specific limitations that affect the reader’s decision or ability to proceed. Avoid “complete” or “production-ready” claims when deployment, recovery, or other applicable workflows remain unverified or undocumented.
