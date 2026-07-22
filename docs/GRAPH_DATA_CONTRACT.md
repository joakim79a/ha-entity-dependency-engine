# Graph Data Contract

Status: Draft for `0.2.0-alpha.1`

This document defines the stable data contract between the Entity Dependency
Engine backend and the future Home Assistant dependency panel.

The visual panel is additive. This contract does not change or replace the
public behaviour protected by `V0_1_COMPATIBILITY_CONTRACT.md`.

## Design principles

1. The data model is a directed graph, even when the panel uses a tree-like
   top-to-bottom layout.
2. Every graph node is unique by `id`.
3. Multiple directed edges may connect the same two nodes when they represent
   different relations or sources.
4. The root entity is displayed in the centre.
5. Upstream dependencies are displayed above the root.
6. Downstream dependants are displayed below the root.
7. Cycles are valid graph structures and must never cause infinite traversal.
8. Broken references remain visible as explicit nodes.
9. Initial responses show one level in each direction.
10. Full expansion is optional and protected by node limits.
11. Friendly name is the primary visible label.
12. Entity ID remains available for identification and management.
13. Runtime Home Assistant state is an optional enrichment layer and is not
    required by the core graph engine.

## Direction definitions

A directed edge always points:

```text
parent / upstream dependency
          |
          v
child / downstream dependant
```

For an edge:

```text
sensor.raw_temperature -> sensor.calculated_temperature
```

- `sensor.raw_temperature` is a parent of
  `sensor.calculated_temperature`.
- `sensor.calculated_temperature` is a child of
  `sensor.raw_temperature`.

These meanings must remain consistent in the backend, panel, reports, labels,
tooltips, and documentation.

## Schema version

Every complete graph response must contain:

```json
{
  "schema_version": 1
}
```

Compatible optional fields may be added without increasing the schema version.

Removing a field, changing a field type, or assigning an incompatible meaning
requires a new schema version.

## Supported scopes

The request scope determines which nodes are selected around the root.

### `direct`

Returns:

- the root
- direct parents
- direct children
- all edges between returned nodes

This is the default panel view.

### `all_parents`

Returns:

- the root
- every reachable upstream node
- all edges between returned nodes

### `all_children`

Returns:

- the root
- every reachable downstream node
- all edges between returned nodes

### `all`

Returns:

- the root
- every reachable upstream node
- every reachable downstream node
- all edges between returned nodes

A node reachable in both directions is returned once and marked with both
roles.

## Complete response

Example:

```json
{
  "schema_version": 1,
  "revision": "2026-07-22T19:42:00+02:00",
  "root_id": "sensor.pool_temperature",
  "scope": "direct",
  "limits": {
    "requested_max_nodes": 250,
    "absolute_max_nodes": 1000
  },
  "statistics": {
    "node_count": 6,
    "edge_count": 5,
    "total_node_count": 6,
    "omitted_node_count": 0,
    "broken_reference_count": 0,
    "cycle_component_count": 0
  },
  "truncated": false,
  "nodes": [],
  "edges": [],
  "warnings": []
}
```

## Response fields

### `schema_version`

Integer contract version.

Current value:

```text
1
```

### `revision`

Opaque string identifying the graph snapshot.

The frontend must not interpret its internal format. A timestamp is acceptable
for the first implementation.

### `root_id`

The entity or graph node selected as the centre.

### `scope`

One of:

- `direct`
- `all_parents`
- `all_children`
- `all`

### `limits`

Contains:

- `requested_max_nodes`
- `absolute_max_nodes`

`requested_max_nodes` includes the root node.

Recommended defaults:

```text
Default: 250
Absolute maximum: 1000
```

### `statistics`

Contains:

- `node_count`: nodes returned in this response
- `edge_count`: edges returned in this response
- `total_node_count`: exact reachable nodes for the requested scope
- `omitted_node_count`: reachable nodes omitted by limits
- `broken_reference_count`: returned broken-reference nodes
- `cycle_component_count`: returned cyclic strongly connected components

### `truncated`

`true` when reachable nodes were omitted due to a node limit.

### `nodes`

Unique graph nodes.

### `edges`

Directed relations between returned nodes.

### `warnings`

Non-fatal build, traversal, enrichment, or truncation warnings.

Warnings are for people and logs. Frontend behaviour must rely on structured
fields instead of parsing warning text.

## Node object

Example:

```json
{
  "id": "sensor.pool_temperature",
  "node_type": "entity",
  "name": "Pool temperature",
  "display_name": "Pool temperature",
  "domain": "sensor",
  "roles": [
    "root"
  ],
  "upstream_depth": null,
  "downstream_depth": null,
  "parent_count": 2,
  "child_count": 3,
  "parents_loaded": true,
  "children_loaded": true,
  "expandable_upstream": true,
  "expandable_downstream": true,
  "broken": false,
  "in_cycle": false,
  "structural": false,
  "runtime": {
    "state": "27.4",
    "state_display": "27.4 °C",
    "available": true,
    "icon": "mdi:pool-thermometer"
  },
  "context": {
    "platform": "template",
    "device_id": null,
    "device_name": null,
    "area_id": null,
    "area_name": null,
    "config_entry_id": "abc123",
    "integration": "template"
  }
}
```

## Required node fields

### `id`

Stable unique graph node identifier.

For entity nodes this is normally the Home Assistant entity ID.

### `node_type`

Examples:

- `entity`
- `automation`
- `script`
- `device`
- `config_entry`
- `area`
- `unknown_entity`
- `unknown`

### `name`

Best stored name from the graph source, or `null`.

### `display_name`

Final label intended for the panel.

Fallback order:

1. current Home Assistant friendly name
2. graph node name
3. entity registry name
4. node ID

The frontend may shorten a visible label for layout, but it must retain the
complete value in a tooltip or detail view.

### `domain`

Entity domain, or `null` for non-entity nodes.

### `roles`

Zero or more of:

- `root`
- `parent`
- `child`
- `ancestor`
- `descendant`

A node may contain both upstream and downstream roles when cycles or multiple
paths make that true.

### `upstream_depth`

Shortest number of incoming-edge steps from the root, or `null`.

Direct parents have:

```text
1
```

### `downstream_depth`

Shortest number of outgoing-edge steps from the root, or `null`.

Direct children have:

```text
1
```

The root has `null` for both depth fields.

### `parent_count`

Total number of direct parents in the complete graph snapshot, not merely the
number currently returned.

### `child_count`

Total number of direct children in the complete graph snapshot.

### `parents_loaded`

Whether all direct parents are present in the current response.

### `children_loaded`

Whether all direct children are present in the current response.

### `expandable_upstream`

`true` when the node has upstream relations that can be displayed or focused.

### `expandable_downstream`

`true` when the node has downstream relations that can be displayed or
focused.

### `broken`

`true` for unresolved or missing references represented as explicit nodes.

### `in_cycle`

`true` when the node belongs to a cyclic strongly connected component or has
a self-referencing edge.

### `structural`

`true` for device, config-entry, area, or other structural nodes.

Structural nodes are excluded from the first panel view unless explicitly
requested later.

### `runtime`

Optional Home Assistant runtime enrichment.

Allowed fields:

- `state`
- `state_display`
- `available`
- `icon`

The core graph serializer may return `null` instead of this object.

### `context`

Optional management and source information.

Allowed fields:

- `platform`
- `device_id`
- `device_name`
- `area_id`
- `area_name`
- `config_entry_id`
- `integration`

Raw storage records, tokens, secrets, and arbitrary parser metadata must not
be exposed through the panel API.

## Edge object

Example:

```json
{
  "id": "edge-2f0d62c8a63d",
  "source": "sensor.raw_temperature",
  "target": "sensor.pool_temperature",
  "relation": "reads",
  "source_parser": "gui_templates",
  "confidence": "certain",
  "label": "Template reference",
  "structural": false,
  "cycle_edge": false
}
```

## Required edge fields

### `id`

Deterministic identifier derived from the edge's public contract fields.

It must remain stable within equivalent graph snapshots.

### `source`

Parent or upstream node ID.

### `target`

Child or downstream node ID.

### `relation`

Existing normalized relation value, for example:

- `reads`
- `writes`
- `triggers`
- `calls_script`
- `belongs_to_device`
- `belongs_to_config_entry`
- `member_of`
- `source_of`
- `depends_on`
- `references`

### `source_parser`

Parser or graph source that discovered the relation.

### `confidence`

One of:

- `certain`
- `probable`
- `dynamic`

### `label`

Human-readable relation label.

The label may be localized by the frontend. Logic must use `relation`, not
this text.

### `structural`

`true` for structural device, config-entry, or area relations.

### `cycle_edge`

`true` when the edge participates in a detected directed cycle.

## Initial loading rules

For `scope: direct`:

1. Include the root.
2. Include every direct parent.
3. Include every direct child.
4. Include every edge whose source and target are both returned.
5. Set `parents_loaded` and `children_loaded` accurately for each node.
6. Never recursively expand a parent or child automatically.

## Full-graph loading rules

For `all_parents`, `all_children`, and `all`:

1. Use cycle-safe breadth-first traversal.
2. Return each node once.
3. Preserve every edge between returned nodes.
4. Calculate shortest upstream and downstream depths independently.
5. Detect cyclic strongly connected components.
6. Apply deterministic ordering.
7. Apply the node limit only after determining the exact reachable set.
8. Report exact truncation statistics.

For `scope: all`, truncation must not allow one direction to consume the entire
limit unfairly. After the root, selection should alternate between upstream
and downstream breadth-first layers where both remain available.

## Deterministic ordering

Responses must be deterministic for an equivalent graph snapshot.

Recommended node ordering:

1. root
2. upstream depth
3. downstream depth
4. display name, case-insensitive
5. node ID

Recommended edge ordering:

1. source
2. target
3. relation
4. source parser
5. confidence

The frontend must not rely on response order for graph correctness, but stable
ordering simplifies tests, caching, and diagnosis.

## Expansion behaviour

The initial panel loads `scope: direct`.

A branch-expansion request must add one direct level for the selected node and
direction without removing already visible nodes.

Expansion directions:

- `parents`
- `children`

The future expansion response may return a complete merged graph or a delta.
That transport decision belongs to the WebSocket API contract, not this core
graph-data contract.

## Panel behaviour derived from this contract

- Root entity appears in the centre.
- Upstream relations appear above.
- Downstream relations appear below.
- Friendly name is primary.
- Entity ID is shown in details and when names are ambiguous.
- Clicking a node selects it.
- Explicit controls expand parents or children.
- The root offers:
  - show all parents
  - show all children
  - show full graph
  - reset to direct view
  - fit graph to viewport
- The graph viewport supports:
  - wheel zoom
  - pinch zoom
  - pan by dragging empty space
  - optional node dragging
  - zoom controls
  - centre control
  - fit-to-screen control

## Compatibility rules

The graph API is separate from the v0.1.0 report action and sensor.

Adding graph fields to internal objects is allowed.

The following are not allowed as part of panel development:

- renaming the existing report action
- changing existing report-action defaults
- removing existing response fields
- renaming the last-report sensor
- changing existing report storage paths
- making public report storage mandatory
- requiring existing users to recreate their config entry

## Security and privacy

The first panel implementation is admin-only.

The backend must:

- authenticate every request through Home Assistant
- require administrator access
- expose only allow-listed node and edge metadata
- avoid returning raw `.storage` records
- avoid returning secrets or tokens
- keep public report storage disabled by default

## Acceptance criteria for `0.2.0-alpha.1`

The milestone is complete when:

1. This contract is committed.
2. A JSON Schema matching this contract is committed.
3. Contract examples validate against the schema.
4. Parent and child directions are covered by tests.
5. Direct scope is covered by tests.
6. All-parent, all-child, and all scopes are covered by tests.
7. Duplicate paths return one node and multiple valid edges.
8. Cycles terminate and are marked.
9. Broken references remain explicit.
10. Truncation is deterministic and accurately reported.
11. Existing v0.1.0 regression tests still pass.
