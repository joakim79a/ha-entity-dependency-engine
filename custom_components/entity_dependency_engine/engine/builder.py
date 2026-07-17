"""Central graph builder for Entity Dependency Engine."""

from __future__ import annotations
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .graph import DirectedGraph
from .parsers import (
    build_device_config_entry_edges,
    build_entity_config_entry_edges,
    build_entity_device_edges,
    parse_automation_relations,
    parse_config_entries,
    parse_derivative_relations,
    parse_device_registry,
    parse_entity_registry,
    parse_group_relations,
    parse_gui_template_relations,
    parse_history_stats_relations,
    parse_integration_relations,
    parse_min_max_relations,
    parse_script_relations,
    parse_switch_as_x_relations,
    parse_threshold_relations,
    parse_utility_meter_relations,
)
from .parsers.base import ParserResult


@dataclass(frozen=True, slots=True)
class BuildPaths:
    entity_registry: Path
    device_registry: Path
    config_entries: Path
    automations: Path
    scripts: Path

    @classmethod
    def from_config_dir(cls, config_dir: str | Path) -> "BuildPaths":
        config_path = Path(config_dir)
        storage = config_path / ".storage"
        return cls(
            entity_registry=storage / "core.entity_registry",
            device_registry=storage / "core.device_registry",
            config_entries=storage / "core.config_entries",
            automations=config_path / "automations.yaml",
            scripts=config_path / "scripts.yaml",
        )


@dataclass(slots=True)
class BuildStatistics:
    node_types: Counter[str] = field(default_factory=Counter)
    edge_parsers: Counter[str] = field(default_factory=Counter)
    edge_relations: Counter[str] = field(default_factory=Counter)
    parser_nodes: Counter[str] = field(default_factory=Counter)
    parser_edges: Counter[str] = field(default_factory=Counter)
    parser_warnings: Counter[str] = field(default_factory=Counter)

    @property
    def total_nodes(self) -> int:
        return sum(self.node_types.values())

    @property
    def total_edges(self) -> int:
        return sum(self.edge_parsers.values())

    @property
    def total_warnings(self) -> int:
        return sum(self.parser_warnings.values())


@dataclass(slots=True)
class BuildResult:
    graph: DirectedGraph
    warnings: list[str]
    statistics: BuildStatistics
    paths: BuildPaths


class GraphBuilder:
    def __init__(self, paths: BuildPaths) -> None:
        self.paths = paths

    @classmethod
    def from_config_dir(cls, config_dir: str | Path) -> "GraphBuilder":
        return cls(BuildPaths.from_config_dir(config_dir))

    def build(self) -> BuildResult:
        graph = DirectedGraph()
        warnings: list[str] = []
        stats = BuildStatistics()

        entities = parse_entity_registry(self.paths.entity_registry)
        devices = parse_device_registry(self.paths.device_registry)
        config_entries = parse_config_entries(self.paths.config_entries)

        self._add_result(graph, "entity_registry", entities, warnings, stats)
        self._add_result(graph, "device_registry", devices, warnings, stats)
        self._add_result(graph, "config_entries", config_entries, warnings, stats)

        structural = [
            ("entity_device_relations",
             build_entity_device_edges(entities.nodes, devices.nodes)),
            ("entity_config_entry_relations",
             build_entity_config_entry_edges(entities.nodes, config_entries.nodes)),
            ("device_config_entry_relations",
             build_device_config_entry_edges(devices.nodes, config_entries.nodes)),
        ]

        for name, result in structural:
            self._add_result(
                graph, name, result, warnings, stats,
                create_missing_nodes=True,
            )

        functional = [
            ("gui_templates",
             parse_gui_template_relations(self.paths.config_entries, entities.nodes)),
            ("utility_meter",
             parse_utility_meter_relations(self.paths.config_entries, entities.nodes)),
            ("derivative",
             parse_derivative_relations(self.paths.config_entries, entities.nodes)),
            ("min_max",
             parse_min_max_relations(self.paths.config_entries, entities.nodes)),
            ("history_stats",
             parse_history_stats_relations(self.paths.config_entries, entities.nodes)),
            ("integration",
             parse_integration_relations(self.paths.config_entries, entities.nodes)),
            ("threshold",
             parse_threshold_relations(self.paths.config_entries, entities.nodes)),
            ("group",
             parse_group_relations(self.paths.config_entries, entities.nodes)),
            ("switch_as_x",
             parse_switch_as_x_relations(self.paths.config_entries, entities.nodes)),
            ("automations",
             parse_automation_relations(self.paths.automations, entities.nodes)),
            ("scripts",
             parse_script_relations(self.paths.scripts, entities.nodes)),
        ]

        for name, result in functional:
            self._add_result(
                graph, name, result, warnings, stats,
                create_missing_nodes=True,
                missing_node_type="unknown_entity",
            )

        stats.node_types = Counter(node.node_type for node in graph.iter_nodes())
        stats.edge_parsers = Counter(edge.source_parser for edge in graph.iter_edges())
        stats.edge_relations = Counter(
            edge.relation_type.value for edge in graph.iter_edges()
        )

        return BuildResult(graph, warnings, stats, self.paths)

    @staticmethod
    def _add_result(
        graph: DirectedGraph,
        parser_name: str,
        result: ParserResult,
        warnings: list[str],
        stats: BuildStatistics,
        *,
        create_missing_nodes: bool = False,
        missing_node_type: str = "unknown",
    ) -> None:
        graph.add_nodes(result.nodes)
        graph.add_edges(
            result.edges,
            create_missing_nodes=create_missing_nodes,
            missing_node_type=missing_node_type,
        )
        stats.parser_nodes[parser_name] += len(result.nodes)
        stats.parser_edges[parser_name] += len(result.edges)
        stats.parser_warnings[parser_name] += len(result.warnings)
        warnings.extend(f"[{parser_name}] {warning}" for warning in result.warnings)


def build_graph(config_dir: str | Path = "/config") -> BuildResult:
    return GraphBuilder.from_config_dir(config_dir).build()
