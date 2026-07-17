"""Dependency reports for one selected graph node."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..graph import DirectedGraph
from ..model import Edge, Node


STRUCTURAL_RELATIONS = {
    "belongs_to_device",
    "belongs_to_config_entry",
    "belongs_to_area",
}


@dataclass(frozen=True, slots=True)
class RelatedNode:
    node: Node
    depth: int
    edges: tuple[Edge, ...]


@dataclass(frozen=True, slots=True)
class DependencyReport:
    root: Node
    direct_parents: tuple[RelatedNode, ...]
    direct_children: tuple[RelatedNode, ...]
    ancestors: tuple[RelatedNode, ...]
    descendants: tuple[RelatedNode, ...]
    broken_references: tuple[RelatedNode, ...]


def build_dependency_report(
    graph: DirectedGraph,
    node_id: str,
    *,
    include_structural: bool = True,
    max_depth: int | None = None,
) -> DependencyReport:
    root = graph.require_node(node_id)

    direct_parents = _related_direct(
        graph,
        node_id,
        direction="incoming",
        include_structural=include_structural,
    )
    direct_children = _related_direct(
        graph,
        node_id,
        direction="outgoing",
        include_structural=include_structural,
    )

    ancestor_depths = _traverse_filtered(
        graph,
        node_id,
        direction="incoming",
        include_structural=include_structural,
        max_depth=max_depth,
    )
    descendant_depths = _traverse_filtered(
        graph,
        node_id,
        direction="outgoing",
        include_structural=include_structural,
        max_depth=max_depth,
    )

    ancestors = _related_from_depths(
        graph,
        ancestor_depths,
        direction="incoming",
        include_structural=include_structural,
    )
    descendants = _related_from_depths(
        graph,
        descendant_depths,
        direction="outgoing",
        include_structural=include_structural,
    )

    broken = tuple(
        item
        for item in (*ancestors, *descendants)
        if item.node.node_type.startswith("unknown")
    )

    return DependencyReport(
        root=root,
        direct_parents=direct_parents,
        direct_children=direct_children,
        ancestors=ancestors,
        descendants=descendants,
        broken_references=broken,
    )


def _related_direct(
    graph: DirectedGraph,
    node_id: str,
    *,
    direction: str,
    include_structural: bool,
) -> tuple[RelatedNode, ...]:
    edges = (
        graph.incoming_edges(node_id)
        if direction == "incoming"
        else graph.outgoing_edges(node_id)
    )

    grouped: dict[str, list[Edge]] = {}

    for edge in edges:
        if not include_structural and _is_structural(edge):
            continue

        related_id = (
            edge.source_node_id
            if direction == "incoming"
            else edge.target_node_id
        )
        grouped.setdefault(related_id, []).append(edge)

    return tuple(
        RelatedNode(
            node=graph.require_node(related_id),
            depth=1,
            edges=tuple(sorted(
                grouped[related_id],
                key=lambda edge: (
                    edge.relation_type.value,
                    edge.source_parser,
                    edge.source_path or "",
                ),
            )),
        )
        for related_id in sorted(grouped)
    )


def _traverse_filtered(
    graph: DirectedGraph,
    start_node_id: str,
    *,
    direction: str,
    include_structural: bool,
    max_depth: int | None,
) -> dict[str, int]:
    visited = {start_node_id: 0}
    queue = [start_node_id]

    while queue:
        current = queue.pop(0)
        current_depth = visited[current]

        if max_depth is not None and current_depth >= max_depth:
            continue

        edges = (
            graph.incoming_edges(current)
            if direction == "incoming"
            else graph.outgoing_edges(current)
        )

        for edge in edges:
            if not include_structural and _is_structural(edge):
                continue

            neighbour = (
                edge.source_node_id
                if direction == "incoming"
                else edge.target_node_id
            )

            if neighbour in visited:
                continue

            visited[neighbour] = current_depth + 1
            queue.append(neighbour)

    visited.pop(start_node_id)
    return visited


def _related_from_depths(
    graph: DirectedGraph,
    depths: dict[str, int],
    *,
    direction: str,
    include_structural: bool,
) -> tuple[RelatedNode, ...]:
    result: list[RelatedNode] = []

    for node_id, depth in sorted(
        depths.items(),
        key=lambda item: (item[1], item[0]),
    ):
        edges = (
            graph.outgoing_edges(node_id)
            if direction == "incoming"
            else graph.incoming_edges(node_id)
        )

        filtered = tuple(
            edge
            for edge in edges
            if include_structural or not _is_structural(edge)
        )

        result.append(
            RelatedNode(
                node=graph.require_node(node_id),
                depth=depth,
                edges=filtered,
            )
        )

    return tuple(result)


def _is_structural(edge: Edge) -> bool:
    return edge.relation_type.value in STRUCTURAL_RELATIONS
