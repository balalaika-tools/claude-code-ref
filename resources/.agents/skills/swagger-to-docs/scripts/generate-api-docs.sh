#!/usr/bin/env bash
# Generate a human-readable Markdown API doc from a Swagger 2.0 JSON file.
#
# Usage:
#   generate-api-docs.sh <input-swagger.json> [output.md]
#
# If output.md is omitted, it defaults to <input-basename>-Documentation.md
# in the current directory.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JQ_FILTER="$SCRIPT_DIR/swagger-to-md.jq"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <input-swagger.json> [output.md]" >&2
  exit 1
fi

INPUT="$1"

if [[ ! -f "$INPUT" ]]; then
  echo "Error: input file not found: $INPUT" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required but was not found on PATH." >&2
  exit 1
fi

if [[ $# -ge 2 ]]; then
  OUTPUT="$2"
else
  BASENAME="$(basename "$INPUT")"
  BASENAME="${BASENAME%.*}"
  OUTPUT="./${BASENAME}-Documentation.md"
fi

if ! jq empty "$INPUT" 2>/dev/null; then
  echo "Error: $INPUT is not valid JSON." >&2
  exit 1
fi

SWAGGER_VERSION="$(jq -r '.swagger // .openapi // "unknown"' "$INPUT")"
if [[ "$SWAGGER_VERSION" != 2.* ]]; then
  echo "Warning: this generator targets Swagger 2.0 documents (found version: $SWAGGER_VERSION)." >&2
  echo "         OpenAPI 3.x uses different structures (requestBody, components/schemas) and may render incompletely." >&2
fi

jq -r -f "$JQ_FILTER" "$INPUT" > "$OUTPUT"

ENDPOINT_COUNT="$(jq '[.paths[] | keys[]] | length' "$INPUT")"
DEFINITION_COUNT="$(jq '.definitions // {} | keys | length' "$INPUT")"

echo "Wrote $OUTPUT"
echo "  Endpoints documented: $ENDPOINT_COUNT"
echo "  Data models documented: $DEFINITION_COUNT"
