# Panel node expansion contract

`entity_dependency_engine/expand_node` expands one visible graph node without changing the selected root.

## Request

```json
{
  "type": "entity_dependency_engine/expand_node",
  "root_id": "sensor.example",
  "node_id": "automation.example",
  "direction": "children",
  "visible_node_ids": ["sensor.example", "automation.example"],
  "max_nodes": 250,
  "include_structural": false,
  "refresh": false
}
```

`direction` is `parents` or `children`. Both `root_id` and `node_id` must already be visible. The response is the complete merged visible graph, not merely a delta. Expansion never changes the root, panel URL, or navigation history.

The response includes an `expansion` object with the expanded node, direction, added IDs, omitted count, and whether that direction was already fully loaded. The absolute limit remains 1000 nodes.

Expansion targets and visible node IDs use generic graph-node strings; only the root must be a Home Assistant entity ID.
