#!/usr/bin/env python3
"""Create a safe baseline MkDocs + Material notes repository."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def yaml_string(value: str) -> str:
    """JSON strings are valid YAML strings and avoid hand-rolled escaping."""
    return json.dumps(value, ensure_ascii=False)


def rendered_files(site_name: str, description: str) -> dict[Path, str]:
    config = f"""site_name: {yaml_string(site_name)}
site_description: {yaml_string(description)}

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
"""

    readme = f"""# {site_name}

{description}

The learning content starts at [`docs/index.md`](docs/index.md).

## Local preview

```bash
python -m pip install -r requirements-docs.txt
python -m mkdocs serve
```

Open the local URL printed by MkDocs. A successful preview reloads after a note is saved.
"""

    index = f"""# {site_name}

> {description}

## Start here

The complete learning paths and contents will be defined here after the collection structure is
approved.
"""

    return {
        Path("mkdocs.yml"): config,
        Path("requirements-docs.txt"): "mkdocs-material\n",
        Path("README.md"): readme,
        Path("docs/index.md"): index,
        Path(".gitignore"): "site/\n",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="New or empty repository directory")
    parser.add_argument("--site-name", required=True, help="Displayed site title")
    parser.add_argument(
        "--description", required=True, help="One-sentence scope of the notes"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = args.target.expanduser().resolve()

    if not args.site_name.strip() or not args.description.strip():
        print("error: site name and description must not be blank", file=sys.stderr)
        return 2

    if target.exists() and not target.is_dir():
        print(f"error: target exists and is not a directory: {target}", file=sys.stderr)
        return 2

    if target.exists() and any(target.iterdir()):
        print(f"error: refusing to scaffold non-empty directory: {target}", file=sys.stderr)
        return 2

    files = rendered_files(args.site_name.strip(), args.description.strip())
    target.mkdir(parents=True, exist_ok=True)

    for relative_path, content in files.items():
        destination = target / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")

    print(f"Created MkDocs notes scaffold at {target}")
    for relative_path in files:
        print(f"  {relative_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
