"""Directed graph implementation for Entity Dependency Engine."""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable, Iterator

from .model import Edge, Node


class DirectedGraph:
    """Stores normalized nodes and directed dependency relations."""

    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._edges: set[Edge] = set()
        self._outgoing: dict[str, set[Edge]] = defaultdict(set)
        self._incoming: dict[str, set[Edge]] = defaultdict(set)

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    def add_node(self, node: Node, *, replace: bool = False) -> None:
        """Add a node.

        Existing identical nodes are ignored. Conflicting duplicates raise
        unless replace=True is explicitly used.
        """
        existing = self._nodes.get(node.node_id)

        if existing is None:
            self._nodes[node.node_id] = node
            return

        if existing == node:
            return

        if not replace:
            raise ValueError(
                f"Node {node.node_id!r} already exists with different data"
            )

        self._nodes[node.node_id] = node

    def add_nodes(self, nodes: Iterable[Node], *, replace: bool = False) -> None:
        for node in nodes:
            self.add_node(node, replace=replace)

    def get_node(self, node_id: str) -> Node | None:
        return self._nodes.get(node_id)

    def require_node(self, node_id: str) -> Node:
        node = self.get_node(node_id)
        if node is None:
            raise KeyError(f"Unknown node: {node_id}")
        return node

    def iter_nodes(self) -> Iterator[Node]:
        return iter(self._nodes.values())

    def add_edge(
        self,
        edge: Edge,
        *,
        create_missing_nodes: bool = False,
        missing_node_type: str = "unknown",
    ) -> None:
        """Add a directed edge.

        Parsers should normally add nodes first. During early parser work,
        create_missing_nodes=True can preserve unresolved references as
        explicit unknown nodes instead of silently dropping them.
        """
        missing = [
            node_id
            for node_id in (edge.source_node_id, edge.target_node_id)
            if node_id not in self._nodes
        ]

        if missing and not create_missing_nodes:
            raise KeyError(f"Edge refers to unknown node(s): {', '.join(missing)}")

        for node_id in missing:
            self.add_node(Node(node_id=node_id, node_type=missing_node_type))

        if edge in self._edges:
            return

        self._edges.add(edge)
        self._outgoing[edge.source_node_id].add(edge)
        self._incoming[edge.target_node_id].add(edge)

    def add_edges(
        self,
        edges: Iterable[Edge],
        *,
        create_missing_nodes: bool = False,
        missing_node_type: str = "unknown",
    ) -> None:
        for edge in edges:
            self.add_edge(
                edge,
                create_missing_nodes=create_missing_nodes,
                missing_node_type=missing_node_type,
            )

    def iter_edges(self) -> Iterator[Edge]:
        return iter(self._edges)

    def outgoing_edges(self, node_id: str) -> frozenset[Edge]:
        self.require_node(node_id)
        return frozenset(self._outgoing.get(node_id, set()))

    def incoming_edges(self, node_id: str) -> frozenset[Edge]:
        self.require_node(node_id)
        return frozenset(self._incoming.get(node_id, set()))

    def children(self, node_id: str) -> frozenset[str]:
        """Return direct downstream nodes."""
        return frozenset(
            edge.target_node_id for edge in self.outgoing_edges(node_id)
        )

    def parents(self, node_id: str) -> frozenset[str]:
        """Return direct upstream nodes."""
        return frozenset(
            edge.source_node_id for edge in self.incoming_edges(node_id)
        )

    def descendants(
        self,
        node_id: str,
        *,
        max_depth: int | None = None,
    ) -> dict[str, int]:
        """Return every reachable downstream node and its shortest depth."""
        return self._traverse(
            node_id,
            direction="outgoing",
            max_depth=max_depth,
        )

    def ancestors(
        self,
        node_id: str,
        *,
        max_depth: int | None = None,
    ) -> dict[str, int]:
        """Return every reachable upstream node and its shortest depth."""
        return self._traverse(
            node_id,
            direction="incoming",
            max_depth=max_depth,
        )

    def _traverse(
        self,
        start_node_id: str,
        *,
        direction: str,
        max_depth: int | None,
    ) -> dict[str, int]:
        self.require_node(start_node_id)

        if max_depth is not None and max_depth < 0:
            raise ValueError("max_depth must be zero or greater")

        visited: dict[str, int] = {start_node_id: 0}
        queue: deque[str] = deque([start_node_id])

        while queue:
            current = queue.popleft()
            current_depth = visited[current]

            if max_depth is not None and current_depth >= max_depth:
                continue

            if direction == "outgoing":
                neighbours = self.children(current)
            elif direction == "incoming":
                neighbours = self.parents(current)
            else:
                raise ValueError(f"Unsupported direction: {direction}")

            for neighbour in neighbours:
                next_depth = current_depth + 1

                if neighbour in visited:
                    continue

                visited[neighbour] = next_depth
                queue.append(neighbour)

        visited.pop(start_node_id)
        return visited

    def shortest_path(
        self,
        source_node_id: str,
        target_node_id: str,
    ) -> list[str] | None:
        """Return one shortest directed path, or None if no path exists."""
        self.require_node(source_node_id)
        self.require_node(target_node_id)

        if source_node_id == target_node_id:
            return [source_node_id]

        previous: dict[str, str | None] = {source_node_id: None}
        queue: deque[str] = deque([source_node_id])

        while queue:
            current = queue.popleft()

            for child in self.children(current):
                if child in previous:
                    continue

                previous[child] = current

                if child == target_node_id:
                    return self._reconstruct_path(previous, target_node_id)

                queue.append(child)

        return None

    @staticmethod
    def _reconstruct_path(
        previous: dict[str, str | None],
        target_node_id: str,
    ) -> list[str]:
        path: list[str] = []
        current: str | None = target_node_id

        while current is not None:
            path.append(current)
            current = previous[current]

        path.reverse()
        return path
