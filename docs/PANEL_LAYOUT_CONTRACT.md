# Panel layered-layout contract

Version: `0.2.0`

The panel renders the visible dependency graph as vertical layers.

- The searched or focused root is level `0`.
- Parents and ancestors use negative levels and are placed above the root.
- Children and descendants use positive levels and are placed below the root.
- Expansion never changes `root_id`, the panel URL, or navigation history.
- Each entity ID is rendered once even when several edges point to it.
- Shared nodes and cycles remain graph structures rather than duplicated tree nodes.
- The graph viewport scrolls vertically and horizontally.
- The root is structurally centred on every layer and is visually stronger than a merely selected node.
- Initial load, Focus here, Reset view, and refresh centre the viewport on the root.
- Expansion preserves the root's current viewport position.
- Edge direction is always source parent to target child.
- Cycle edges are drawn with a distinct dashed style.
