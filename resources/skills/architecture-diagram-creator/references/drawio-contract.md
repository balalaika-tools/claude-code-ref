# Deterministic draw.io XML contract

Generate UTF-8, uncompressed `<mxfile><diagram><mxGraphModel><root>…` with root cells `0` and `1` (`parent="0"`). Use unique descriptive IDs per page, `vertex="1"` or `edge="1"`, and finite positive vertex geometry. Build XML with an XML library to escape labels correctly.

Use custom style fields `archRole=card|icon|label|boundary|title|badge|legend|legend-badge|legend-step;` and `archStep=1;` (on flow edges, both badge types and legend descriptions). These are inert draw.io style metadata used by the validator. The graph model uses `archLegend="1"` by default or `archLegend="0"` for an explicit opt-out. The validator requires this metadata; arbitrary old files are not treated as fully checked.

Set `archProvider="aws"`, `"neutral"`, `"mixed"` or the selected provider name on the graph model. The neutral check rejects AWS stencil references; review names and embedded brand assets semantically as well.

## Cards and containers

Architectural cards are visible rectangle vertices at `parent="1"`, `archRole=card;container=1;collapsible=0;perimeter=rectanglePerimeter;rounded=0;`. Put all architectural cards, boundaries, edges and annotations in root coordinates to eliminate cross-group coordinate ambiguity. Draw decorative `archRole=boundary` rectangles first, behind cards. Logical/deployment nesting is visual; do not silently imply a deployment boundary that evidence doesn't support.

Put the icon (nominally 48 × 48, with optical adjustments for differently proportioned artwork) and any internal text under its card using local coordinates, `connectable="0"`, `archRole=icon` or `archRole=label`. Keep icons centered, undistorted and within the card; see [optical sizing](icons.md#optical-size-consistency). Card labels must fit inside. Separate diagrams/pages are preferable to a component card containing many independently connected components. Rectangular cards deliberately make the visible perimeter identical to the validated rectangle; don't add rounded corners without updating validation for that shape.

## Endpoints and routes

Set `source` and `target` to **card IDs**, not icon IDs. Define face anchors with `exitX/Y`, `entryX/Y`: one coordinate exactly 0 or 1 and the other strictly between 0 and 1. Use zero `exitDx/Dy`, `entryDx/Dy`, `exitPerimeter=1;entryPerimeter=1;`. Space anchors ≥20 px on the same face.

For new diagrams, use explicit orthogonal polylines with `edgeStyle=none;noEdgeStyle=1;rounded=0;curved=0;endArrow=block;endFill=1;strokeWidth=1.5;`. Set all intermediate bends in `<Array as="points">` under `<mxGeometry relative="1" as="geometry">`. Every consecutive point including the two card anchors must be axis-aligned. The first and last segment must extend outward from the respective face for ≥20 px. A straight line needs no waypoints if its anchors align.

This intentionally fixes the polyline rather than asking `orthogonalEdgeStyle` to synthesize unknown bends. Draw.io auto-routing is useful while editing, but XML waypoints alone do not reveal its final rendered segments. If using auto-routing in an imported/editable layout, render it and resolve the actual path before asserting geometric validation; the bundled validator reports it as unsupported. After moving cards, recompute waypoints and rerun checks.

```xml
<mxCell id="flow-api-worker" edge="1" parent="1"
  source="card-api" target="card-worker"
  style="edgeStyle=none;noEdgeStyle=1;rounded=0;curved=0;exitX=1;exitY=0.5;exitDx=0;exitDy=0;exitPerimeter=1;entryX=0;entryY=0.5;entryDx=0;entryDy=0;entryPerimeter=1;endArrow=block;endFill=1;strokeWidth=1.5;archStep=1;fontFamily=Helvetica;">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

Small boundary-header SVGs may use non-connectable root-level `archRole=icon` vertices with explicit geometry; reserve separate space for the boundary title and keep flow endpoints on component cards. These standalone icon rectangles participate in overlap and route-clearance checks.

Annotations (including optional edge labels) have explicit root-coordinate rectangles, not relative edge labels, so overlap checks can evaluate them. A 28 × 28 `archRole=badge;archStep=1` carries `value="1"`. Its sidebar counterpart is a separate 40 × 38 `archRole=legend-badge;archStep=1` with the same value and blue/black/white graphic. The adjacent `archRole=legend-step;archStep=1` contains only the bold action title and concise description. Both sit inside the root-level `archRole=legend` panel, using root coordinates. Each numbered step needs one canvas badge, one sidebar badge, one description and at least one edge. Multiple edges may share a step; decorative relationships can be unnumbered. Use the shared badge styles in [layout-and-quality.md](layout-and-quality.md).

The orange title separator is a non-connectable root-level vertex with `archRole=title;shape=line;strokeColor=#FF9900;strokeWidth=2;`, an empty value, and a positive geometry height (e.g. 2 px). It is decoration, not an architectural edge.

Self-loops and return flows need distinct anchors and exterior waypoints. Crossing enclosing system/VPC boundaries is allowed; penetrating any **component card**, including source/target after departure, is an error.
