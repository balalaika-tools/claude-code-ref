# MkDocs + Material Output

Read this reference when creating a new notes collection, adding MkDocs to an existing collection,
or changing its site configuration.

## Default layout

Use the conventional `docs/` source directory. Keep generated output in `site/` and do not commit
it unless the user explicitly wants built artifacts versioned.

```text
notes-repo/
├── README.md
├── mkdocs.yml
├── pyproject.toml
├── uv.lock
├── .github/
│   └── workflows/
│       └── docs.yml
└── docs/
    ├── index.md
    ├── assets/
    └── fundamentals/
        ├── index.md
        ├── 01_first_result.md
        └── 02_why_it_works.md
```

`docs/index.md` owns the complete structure, contents tables, and reading paths. The repository
`README.md` is only the contributor-facing doorway: describe the scope, link to `docs/index.md`,
and include the install and preview commands.

## Scaffold a new collection

After the user approves the proposed learning structure, create the baseline with the bundled
script:

```bash
python <skill-directory>/scripts/scaffold_mkdocs.py <target-directory> \
  --site-name "{Topic} Notes" \
  --description "{One-sentence scope}"
```

The target may be absent or empty. The script refuses a non-empty directory and never overwrites
files. It creates only the deterministic shell — `mkdocs.yml`, `pyproject.toml`, `README.md`,
`docs/index.md`, `.github/workflows/docs.yml`, and `.gitignore` — afterward, replace the skeletal
`docs/index.md` with the site-index template, add the approved sections and notes, and expand `nav`
in learning order. Do not use the script to migrate an existing repository.

## Dependency management: `uv`, not `pip`

Manage the documentation dependency with **`uv`**, not `pip` + a `requirements-docs.txt` file.
Declare it in `pyproject.toml`:

```toml
[project]
name = "{topic-slug}-notes"
version = "0.1.0"
description = "{One-sentence scope}"
requires-python = ">=3.10"
dependencies = [
    "mkdocs-material",
]
```

Do not invent a version pin. Run `uv sync` once after scaffolding to create `uv.lock` and the local
`.venv/`; commit `pyproject.toml` and `uv.lock`, and keep `.venv/` out of version control. If the
repository already has an established dependency-management convention (an existing `pyproject.toml`
with Poetry, or another tool the user is already using), add Material for MkDocs there instead of
introducing a competing setup — but default to `uv` for a new collection.

## Baseline configuration

Start from this configuration and replace the placeholders and navigation. Keep `nav` explicit so
the published learning order is reviewable.

```yaml
site_name: "{Topic} Notes"
site_description: "{One-sentence scope}"

theme:
  name: material
  features:
    - navigation.indexes
    - navigation.sections
    - navigation.top
    - search.highlight
    - search.suggest
    - content.code.copy

plugins:
  - search

markdown_extensions:
  - admonition
  - attr_list
  - md_in_html
  - pymdownx.details
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true
  - pymdownx.highlight:
      anchor_linenums: true
  - pymdownx.inlinehilite

nav:
  - Home: index.md
  - Fundamentals:
      - fundamentals/index.md
      - "First result": fundamentals/01_first_result.md
      - "Why it works": fundamentals/02_why_it_works.md
```

Add `site_url`, repository links, or analytics only when the user supplies the corresponding values
or asks for them. Do not guess a public URL or repository. Deployment configuration for GitHub
Pages lives in the workflow below, not in `mkdocs.yml`.

## Repository README

Keep the commands copyable and aligned with `pyproject.toml`:

````markdown
# {Topic} Notes

The learning content starts at [`docs/index.md`](docs/index.md).

## Local preview

```bash
uv sync
uv run mkdocs serve
```

Open the local URL printed by MkDocs. A successful preview reloads after a note is saved.
````

If the repository already has an established dependency workflow (Poetry, or another tool the user
is already using), express the same two actions with that tool instead of adding a competing setup.

## GitHub Pages deployment (required)

Every MkDocs collection this skill scaffolds or migrates gets a GitHub Actions workflow that
publishes it to GitHub Pages. Write this unconditionally when creating or migrating a collection
that lives in a Git repository — do not wait for the user to ask for CI/CD. Only skip it when the
user explicitly says they don't want the site published, or the repository has no relationship to
GitHub at all (no `.git` remote pointing at GitHub, no `gh` usage, no existing `.github/`).

Create `.github/workflows/docs.yml`:

```yaml
name: Deploy docs

on:
  push:
    branches: [main]

permissions:
  contents: write

concurrency:
  group: docs-deploy
  cancel-in-progress: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync
      - run: uv run mkdocs gh-deploy --force
```

Rules for this workflow:

- Trigger on push to the repository's actual default branch (`main` above — confirm the real
  default branch name rather than assuming it).
- `permissions: contents: write` is required because `mkdocs gh-deploy` pushes to the `gh-pages`
  branch using the workflow's own token; do not broaden permissions beyond this.
- Use `astral-sh/setup-uv` to install `uv` in the runner, then `uv sync` and
  `uv run mkdocs gh-deploy --force` — the same two local-preview actions, run non-interactively.
  `--force` is required because `gh-deploy` otherwise refuses to overwrite a `gh-pages` history it
  does not recognize as its own.
- If the repository does not use `uv` (see *Dependency management* above), swap the install step for
  that tool's non-interactive equivalent; keep the rest of the job identical.
- After adding the workflow, tell the user to enable GitHub Pages for the repository once (Settings
  → Pages → Source: "Deploy from a branch" → `gh-pages` branch), since the workflow cannot do this
  itself on a repository's first deploy.
- Do not invent a custom domain, `site_url`, or CNAME unless the user provides one.

## Navigation rules

- Put `Home` first and order later groups by learning progression.
- Use each section's `index.md` as the unlabeled first entry in that section; Material renders it as
  the section landing page when `navigation.indexes` is enabled.
- Include each learner-facing page exactly once. A page may participate in several reading paths
  through links on the landing pages without being duplicated in `nav`.
- Keep repository files, generated files, and contributor-only material outside `docs/`.
- Update relative links when moving Markdown into `docs/`; do not rely on MkDocs to repair them.

## Verification

From the collection root, run:

```bash
python -m mkdocs build --strict
```

Success means the command exits with status 0 and writes the site to `site/`. Also open a local
preview at least once for a newly scaffolded collection and check the home page, section indexes,
search, code-copy buttons, and next-note links. If the dependency is unavailable and installing it
is outside the current authorization, report the build as unverified rather than skipping it
silently.

## Existing collections

When the user asks to migrate an existing collection:

1. Inventory all Markdown files and current inbound links.
2. Move learner-facing content under `docs/`, renaming landing pages to `index.md` only where that
   improves the site hierarchy.
3. Repair relative links and build an explicit `nav` from the existing reading order.
4. Keep a concise repository `README.md` rather than a second copy of the landing page.
5. Run both the note validator and the strict MkDocs build before declaring the migration complete.

Do not perform this migration merely because a user asks to add one note to an existing repository.
