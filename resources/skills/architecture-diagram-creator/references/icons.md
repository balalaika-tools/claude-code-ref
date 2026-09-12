# Icon discovery, packages and custom brands

For a named technology, prefer its specific icon: verified product-specific native stencil → approved matching local asset → official provider package/brand site or project's official repository → labeled generic symbol only as a fallback. A cached generic role icon does not outrank a missing product logo. A missing icon is not a reason to invent a logo or imply another service. Search the web when an asset is missing, using the technology's official source. Preserve its proportions and colors.

## Unfamiliar services and missing icons

Do not guess what an unfamiliar service does from its name or logo. Read permitted repository integration code and the service's official documentation/site to establish its identity and architectural role. Distinguish similarly named projects, hosted offerings and self-hosted software.

1. Determine whether the component names a specific product/technology or only a responsibility. For named technologies, prefer their own recognizable icons in both overviews and focused views, including vendor-neutral diagrams. “Neutral” alone does not request removal of technology identities. Use semantic pictograms directly for unnamed roles or when the user explicitly requests technology-agnostic/no-brand presentation.
2. Search the existing project icon catalog and the relevant verified stencil library for that exact technology. If absent, search the web for its official brand/media kit or official repository before choosing a generic icon. Prefer an exact product/subproduct mark; if none exists, an official parent-project mark is acceptable when it accurately represents the named component. Do not invent a subproduct logo. Prefer an actual downloadable SVG; do not use a search-result thumbnail, another vendor's logo, or an invented brand mark.
3. For unnamed roles or generic fallbacks after the product-icon search, prefer the bundled Lucide set or another matching icon from the same official library. Choose by meaning (workflow, queue, model, search, tool, observability), not visual resemblance alone. Do not force every unfamiliar role into one generic square or robot icon.
4. Record source URL, hash and license/usage note with the local asset; retain required license notices when bundling or embedding library icons. Register and embed it with the helper below. Preserve official brand geometry/colors; neutral library glyphs may adopt the diagram's role colors.
5. If no reliable asset is available or browsing is unavailable, use a clearly labeled neutral pictogram for the verified responsibility and disclose the fallback. If the service's identity is itself unclear, ask a focused question instead of presenting a guess as fact.

Inspect the embedded icon at 48 × 48 in a draw.io render: recognizable silhouette, consistent stroke/optical scale, adequate contrast, and no clipping. The surrounding card remains the connection target.

## Optical size consistency

Compare the **visible artwork**, not just the XML image rectangle. Two 48 × 48 cells may look very different when one SVG contains large transparent margins. Use 48 × 48 as the nominal icon size, center each mark in the same card icon area, and normalize surplus SVG whitespace with a viewBox around the artwork plus a small breathing margin. Preserve the original source and record normalization in the asset catalog.

Preserve aspect ratio, brand paths and colors. A wide mark can need a wider image cell (for example 64 × 48) to have comparable visible area/weight to a square icon. Recenter the image cell and retain clearance from the heading and service label; do not stretch the logo into a square or crop visible strokes. Any brand-required clear space takes priority over removing whitespace. Verify in an actual render beside neighboring AWS/Lucide icons, not by dimensions alone.

The bundled Langfuse display asset demonstrates this: trimmed surplus viewBox whitespace, original paths/colors, and a centered 64 × 48 image cell. Its original SVG is retained in the brand asset directory. This is an optical adjustment for that mark, not a mandatory size for every custom icon.

## AWS package

Open [AWS Architecture Icons](https://aws.amazon.com/architecture/icons/) and resolve the current asset-package ZIP link. Download it to a project cache (for example `.cache/architecture-icons/aws/`) with the helper:

```bash
python3 <skill>/scripts/icon_assets.py package '<official-https-zip-url>' .cache/architecture-icons/aws
```

This extracts only SVG files to a new destination, blocks traversal, limits download/expansion sizes, and records URL, download date and SHA-256 in `package.json`. Search the extracted filenames for the service. Reuse an existing cache instead of downloading for each diagram. If network access or the package is unavailable, use a verified native stencil or labeled generic fallback and disclose the substitution.

## Register and embed

For an official brand such as Langfuse, find the actual SVG source, download it locally using an available HTTP tool, then register it. A provided local asset is also valid input; do not claim its provenance is verified if the original source is unknown.

```bash
python3 <skill>/scripts/icon_assets.py register icons/langfuse-brand.svg \
  --name langfuse --source 'user-provided local asset; upstream unverified' \
  --license-note 'Brand asset; review upstream usage terms when redistributing' \
  --catalog icons/catalog.json
python3 <skill>/scripts/icon_assets.py embed icons/langfuse-brand.svg --output /tmp/langfuse-uri.txt
```

Registration records the local path, source, retrieval/registration date, SHA-256 and usage note. Record an actual upstream URL when known. For an extracted AWS SVG, record the package source URL and its package manifest. Keep the catalog with project icons; don't write downloaded brands into the installed skill automatically.

The helper accepts self-contained SVGs only (no scripts, external references, event handlers or foreign HTML). It conservatively rejects unsupported SVG features; get a simpler official asset or use a generic symbol rather than stripping content blindly. It emits the draw.io image-style encoding `data:image/svg+xml,<base64>`; SVG content remains a bitmap-independent embedded image, while cards/text/edges remain editable native cells.

Use that entire URI as `image=` in `shape=image;imageAspect=1;aspect=fixed;archRole=icon;` on a non-connectable child of the card. Start with 48×48 geometry and apply the optical-size procedure above when needed. XML-escape the style via an XML library. Do not leave `file://`, an absolute local filename, or a remote image URL in the delivered XML. Preserve the original SVG alongside the catalog for reuse. Render to verify the image in the target draw.io version.

An icon's identity does not decide topology. Langfuse may be a hosted integration or an application service inside the deployment. Use a neutral “Observability” symbol when the component is generic or the user explicitly abstracts away Langfuse. For example, a card named “NATS JetStream” should first seek a verified JetStream mark, then an appropriate official NATS mark, and use a Lucide broker/queue pictogram only if no suitable reliable asset is available. A card named only “Message broker” can use Lucide immediately.
