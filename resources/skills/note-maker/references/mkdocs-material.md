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
├── requirements-docs.txt
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
files. It creates only the deterministic shell; afterward, replace the skeletal `docs/index.md`
with the site-index template, add the approved sections and notes, and expand `nav` in learning
order. Do not use the script to migrate an existing repository.

## Dependency file

Create `requirements-docs.txt` with the direct documentation dependency:

```text
mkdocs-material
```

Do not invent a version pin. If the repository already has a dependency-management convention,
add Material for MkDocs there instead and preserve its locking policy.

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

Add `site_url`, repository links, analytics, extra CSS, or deployment configuration only when the
user supplies the corresponding values or asks for them. Do not guess a public URL or repository.

## Repository README

Keep the commands copyable and aligned with the generated dependency file:

````markdown
# {Topic} Notes

The learning content starts at [`docs/index.md`](docs/index.md).

## Local preview

```bash
python -m pip install -r requirements-docs.txt
python -m mkdocs serve
```

Open the local URL printed by MkDocs. A successful preview reloads after a note is saved.
````

If the repository uses `uv`, Poetry, or another established workflow, express the same two actions
with that tool instead of adding a competing setup.

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
