# Test suite structure

Organize tests so a reader can answer two questions from the path alone:

1. What execution environment and isolation does this test require?
2. Which business capability or technical boundary owns the behavior?

Execution profile is the first axis once a suite has more than one profile.
Ownership is the second axis when a profile grows enough to need it. Do not use
folder depth as a substitute for understanding what a test proves.

## Member ownership

Each deployable or internal library owns its tests beside its source:

```text
services/<service>/tests/
libs/<library>/tests/
```

A service test may use public internal-library APIs declared as dependencies. It
must not import another deployable's private package or test helpers. Put a
cross-service system test in an explicitly repository-owned E2E suite or a
dedicated test deployable rather than hiding it below one participant.

Production code never imports `tests`, test builders, or fakes. Do not move
general-purpose test support into production merely to make it importable.

## Classification decision

Use the first matching category below. This order makes the top-level folders
mutually exclusive even though ordinary testing terminology sometimes overlaps:

1. **`e2e/`** starts the deployable, exercises a complete business flow, or
   crosses multiple real outer boundaries.
2. **`integration/`** exercises at least one concrete outer implementation
   against real disposable infrastructure, an actual filesystem/process, or a
   disposable protocol endpoint or service emulator, without proving the whole
   deployable flow.
3. **`contract/`** verifies a shipped or externally consumed compatibility
   surface without requiring the live integration above: package exports,
   configuration documents, CLI/deployment entry points, schemas, static
   migration topology, or sanitized wire artifacts.
4. **`unit/`** runs wholly in process with deterministic collaborators, fakes,
   stubs, mock transports, or in-memory framework harnesses.

Classify by what the test actually executes, not by the package under test, its
filename, or the presence of a mock. A concrete adapter tested with an injected
fake SDK client is still a unit test of that adapter. The same adapter against a
real disposable service belongs in integration.

| Behavior under test | Canonical placement |
| --- | --- |
| Pure domain rule or application action using port fakes | `unit/domain/` or `unit/application/` |
| API router through an in-process client with outer ports replaced | `unit/api/` |
| Bootstrap construction/lifecycle with injected constructors | `unit/bootstrap/` |
| Concrete AWS/HTTP/GenAI adapter with a fake SDK or model handle | `unit/adapters/` or `unit/genai/` |
| Repository queries against disposable PostgreSQL | `integration/db/` |
| Concrete broker, object-store, browser, or filesystem boundary against its real local implementation | `integration/adapters/` |
| Alembic upgrade/downgrade against a database | `integration/migrations/` |
| Static Alembic revision chain, package exports, config/YAML shape, Docker or CLI entry point | `contract/` under the matching owner |
| Whole local workflow from process boundary through multiple real components | `e2e/` |

An optional test that reaches a shared staging system, paid model, or other
non-disposable provider is a **live test**, never part of the ordinary unit or
integration suite. Give it an explicit opt-in location or marker, bounded inputs
and cost, and a CI job that cannot run accidentally.

## Canonical tree

Create only the branches the member uses:

```text
tests/
├── conftest.py                     # Lightweight fixtures/policy shared by all profiles
├── unit/
│   ├── application/
│   │   └── test_email_admission.py
│   ├── domain/
│   │   ├── test_authentication.py
│   │   └── test_email_parsing.py
│   ├── adapters/
│   │   └── aws/
│   │       └── test_sqs_serialization.py
│   ├── genai/
│   │   └── email_classification/
│   │       ├── test_prompts.py
│   │       └── test_classifier.py
│   └── bootstrap/
│       └── test_runtime.py
├── integration/
│   ├── conftest.py                 # Disposable infrastructure lifecycle only
│   ├── db/
│   │   └── test_admission_repository.py
│   └── adapters/
│       └── aws/
│           └── test_raw_email_store.py
├── contract/
│   ├── config/
│   │   └── test_settings_documents.py
│   ├── deployment/
│   │   └── test_entrypoints.py
│   └── migrations/
│       └── test_revision_chain.py
├── e2e/
│   ├── conftest.py                 # Whole-system lifecycle and prerequisites
│   └── test_inbound_response_flow.py
├── fixtures/                       # Sanitized static artifacts shared across profiles
│   └── inbound_email/
└── support/                        # Truly cross-profile builders/fakes, when demonstrated
```

This is a placement policy, not starter boilerplate. A library with four
in-process tests can keep them flat at `tests/`. Once a second execution profile
exists, introduce the relevant top-level profile folders and move all tests into
an unambiguous category; do not leave an unexplained mixture at the root.

## Growth inside a profile

Apply flat-first within `unit/`, `integration/`, `contract/`, `e2e/`, and each
owner below them:

- Keep a few cohesive test modules flat while their owner and setup are obvious.
- Add a source-boundary or business-capability directory when several modules
  share that owner, require narrower fixtures, or create naming collisions.
- Mirror stable source boundaries such as `application`, `domain`, `adapters`,
  `genai`, `db`, and `bootstrap` selectively, not automatically.
- Prefer a capability package such as
  `unit/application/email/` when several actions belong together. Do not create
  one test package per production class or function.

A test module owns one cohesive behavior and one execution profile. Split it
when its tests require different infrastructure, target unrelated production
owners, need different fixture scope, or make a conjunction necessary in the
filename. File length is only a review signal; scenario tables and focused test
cases may legitimately be long.

Use precise names such as `test_email_admission.py`,
`test_source_projection_repository.py`, and `test_sqs_serialization.py`. The
profile is already in the path, so avoid redundant suffixes such as `_unit` and
`_integration`. Avoid catch-all or multi-owner names such as `test_domain.py`,
`test_contracts.py`, `test_runtime_adapters.py`,
`test_auth_parsing_classification.py`, and `test_worker_and_telemetry.py`.

## Fixtures, builders, fakes, and captured data

Fixture visibility should reveal resource cost:

- Root `tests/conftest.py` contains only lightweight fixtures, safety hooks, and
  collection policy genuinely shared across profiles.
- `integration/conftest.py` owns database, broker, object-store, browser, and
  other disposable-infrastructure lifecycle. Put a capability-specific
  `conftest.py` still lower when only that slice needs it.
- `e2e/conftest.py` owns whole-process startup, readiness, and teardown.
- A fixture belongs at the narrowest common ancestor of its consumers. Do not
  promote it to root merely to avoid a local duplicate.
- Do not hide reusable builders, fake port implementations, recorders, or large
  scenario DSLs in `conftest.py`. Put them in a precisely named support module
  beside their consumer, or in `support/` after real reuse exists.
- Never import `conftest.py` as a helper module; pytest owns its discovery.

Keep static `.json`, `.eml`, workbook, wire-envelope, and similar inputs below
`fixtures/<capability>/` at the narrowest profile that owns them. Promote them to
root `fixtures/` only when multiple profiles use the same artifact. Captured
external data must be sanitized, minimal, stable, and versioned when its schema
changes. Document provenance or regeneration only when it is not evident from
the fixture and test.

Test support imports must be explicit and collision-safe. In a monorepo, do not
add several member `tests/` directories to a global `pythonpath` and rely on bare
imports such as `from builders import ...`. Keep a helper local when possible;
when it must be imported broadly, use an unambiguous member-qualified test-support
package. Omit `tests/__init__.py` unless package semantics are intentionally
needed, and prefer pytest's importlib mode for independently owned test trees.

## Dependency and isolation rules

- Unit tests for application actions replace effects at port or repository
  boundaries. They do not patch boto3, LangChain, SQLAlchemy sessions, or HTTP
  internals through several layers of production code.
- Unit tests for a concrete adapter may fake its direct SDK/model/client
  collaborator because that implementation is the subject under test.
- Bootstrap tests verify selection, construction, lifecycle, and disposal
  separately from business behavior.
- Integration tests own disposable targets, unique data, deterministic reset or
  cleanup, and bounded timeouts. A destructive database reset must refuse an
  ordinary service `DATABASE_URL` and require an explicitly test-scoped target.
- Tests do not depend on execution order, shared mutable state, live wall-clock
  sleeps, or data left by a previous test. Inject clocks and sleep functions for
  deterministic time behavior.
- Ordinary unit tests make no network calls, launch no browser, call no live
  model, and require no developer credentials.
- Business behavior is tested through public application actions and stable
  contracts. Private helpers are tested directly only when they carry a
  substantial independent rule that has not yet earned a public owner.

## Markers and CI selection

Folders communicate navigation and fixture scope; markers communicate runtime
selection. Keep them aligned:

- Register markers and enable strict marker validation.
- Mark every integration, E2E, and live test consistently, either explicitly or
  through a narrowly scoped collection hook. Do not rely only on `_integration`
  in a filename.
- Use markers for execution cost and prerequisites, not for business packages
  such as `domain` or `email`.
- The ordinary fast suite excludes live tests and any profile whose
  prerequisites are not provisioned. An integration CI job provisions a
  disposable dependency explicitly and selects only that profile.
- A selected integration or E2E job fails fast when its required target is
  absent; it must not report success because every intended test silently
  skipped.
- Coverage policy may combine profiles, but each profile must also have a stable
  direct command so failures can be reproduced locally.

## Structure-only migration

Restructure tests without redesigning behavior:

1. Inventory every test module by actual execution profile, behavioral owner,
   fixtures, support imports, markers, and CI command.
2. Split mixed-profile and mixed-owner modules before moving them. Preserve test
   assertions and names unless a rename is necessary to expose ownership.
3. Create only the profile and owner directories the current suite needs.
4. Move expensive fixtures from root `conftest.py` to their narrowest profile or
   capability; extract importable support code from `conftest.py` into precise
   modules.
5. Move sanitized artifacts with their owner and update paths through local
   fixture helpers rather than repository-wide constants.
6. Replace ambiguous bare test-helper imports with collision-safe imports; do
   not broaden global `pythonpath` to make the move work.
7. Align markers, pytest configuration, pre-commit/pre-push paths or filters,
   local commands, and CI selectors with the new directories.
8. Move one profile or capability slice at a time. Run that slice after each
   move, then finish with the full unit, contract, integration, and E2E commands
   that the repository supports.

Do not combine a folder-only migration with production refactoring, test
rewrites, fixture redesign, or coverage expansion unless the user explicitly
requests those changes.

## Review questions

- Can every test's execution cost and owner be inferred from its path?
- Does any file mix unit and integration behavior or unrelated boundaries?
- Are expensive or destructive fixtures scoped below the profile that needs
  them?
- Are contract tests validating a real compatibility surface rather than acting
  as a miscellaneous bucket?
- Are E2E and live tests explicit, bounded, and excluded from accidental runs?
- Do helper imports remain unambiguous in a repository-wide pytest and mypy run?
- Can application tests replace effects through ports instead of patching
  concrete SDK internals?
- Do CI jobs select real profiles and fail when required infrastructure is
  missing?
