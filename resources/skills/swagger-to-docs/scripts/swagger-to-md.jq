# swagger-to-md.jq
#
# Converts a Swagger 2.0 JSON document into a single human-readable Markdown
# file: overview, services list, endpoints grouped by tag (with parameter and
# response tables), and a data-model appendix built from `definitions`.
#
# Usage:
#   jq -r -f swagger-to-md.jq input-swagger.json > output.md
#
# Designed to be resilient to sparse/missing fields (no `parameters`, no
# `description`, refs vs. inline schemas, arrays of refs, etc.) since
# real-world Swagger docs are rarely fully populated.

# ---- helpers -----------------------------------------------------------

def refName:
  if type == "string" then sub(".*/"; "") else . end;

# Resolve a "type" for a raw schema object (used for definitions/properties
# and for response/parameter `schema` blocks).
def schemaType:
  if . == null then "-"
  elif has("$ref") then (."$ref" | refName)
  elif .type == "array" then
    "array<" + ((.items."$ref"? // .items.type? // "object") | refName) + ">"
  else (.type // "object")
  end;

# Resolve a "type" for a Swagger parameter, which is either a primitive
# `type` field or a `schema` block.
def paramType:
  if .type then .type
  elif .schema then (.schema | schemaType)
  else "object"
  end;

def mdEscape:
  gsub("\\|"; "\\|") | gsub("\n"; " ");

def paramTable:
  if (. == null) or (length == 0) then "_None_\n"
  else
    "| Name | In | Required | Type |\n|---|---|---|---|\n" +
    ([.[] | "| \(.name // "-") | \(.in // "-") | \(.required // false) | \(paramType) |"] | join("\n")) + "\n"
  end;

def respTable:
  "| Code | Description | Schema |\n|---|---|---|\n" +
  ([to_entries[] | "| \(.key) | \(.value.description // "" | mdEscape) | \(.value.schema | schemaType) |"] | join("\n")) + "\n";

# ---- document assembly --------------------------------------------------

def header:
  "# " + (.info.title // "API Documentation") + "\n\n" +
  "This is a human-readable reference generated from a Swagger 2.0 document" +
  (if .info.description then ": " + .info.description else "." end) + "\n\n" +
  (if .host then "- **Host:** `\(.host)`\n" else "" end) +
  (if .basePath then "- **Base path:** `\(.basePath)`\n" else "" end) +
  (if .info.version then "- **Version:** \(.info.version)\n" else "" end) +
  (if .info.contact then
    "- **Contact:** " +
    ([.info.contact.email, .info.contact.url] | map(select(. != null)) | join(" — ")) + "\n"
  else "" end) +
  "\n" +
  (if .host and .basePath then
    "> Full URLs are formed as `https://{host}{basePath}{path}`, e.g.\n" +
    "> `https://\(.host)\(.basePath)" +
    ((.paths // {} | keys | first) // "/example") + "`\n\n"
  else "" end);

def servicesOverview:
  "## Services Overview\n\n" +
  ((.tags // []) | map("- **\(.name)** — \(.description // "")") | join("\n")) + "\n";

def endpointEntry:
  "### \(.method | ascii_upcase) `\(.path)`\n" +
  "**\(.v.summary // .v.operationId // "")**\n\n" +
  (if .v.description then "\(.v.description)\n\n" else "" end) +
  "**Parameters**\n\n" + (.v.parameters | paramTable) + "\n" +
  "**Responses**\n\n" + (.v.responses // {} | respTable) + "\n---\n";

def endpointsSection:
  "## Endpoints\n\n" +
  ((.paths // {}) | to_entries
    | map(.key as $path | .value | to_entries[]
        | {tag: (.value.tags[0] // "misc"), method: .key, path: $path, v: .value})
    | sort_by(.tag)
    | group_by(.tag)
    | map("### " + .[0].tag + "\n\n" + (map(endpointEntry) | join("\n")))
    | join("\n")) + "\n";

def definitionEntry:
  "### \(.key)\n" +
  (if (.value.properties // {} | length) == 0 then "_No properties defined_\n"
   else ([.value.properties | to_entries[] | "- \(.key): \(.value | schemaType)"] | join("\n")) + "\n"
   end);

def dataModelsSection:
  "## Data Models\n\n" +
  "These are the request/response body schemas (`definitions`) referenced by the endpoints above. " +
  "Only top-level fields are listed; nested object types reference other model names in this section.\n\n" +
  ((.definitions // {}) | to_entries | sort_by(.key) | map(definitionEntry) | join("\n"));

# ---- entry point ---------------------------------------------------------

header + "\n---\n\n" + servicesOverview + "\n---\n\n" + endpointsSection + "\n---\n\n" + dataModelsSection
