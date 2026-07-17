"""Core data models for Entity Dependency Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping


class Confidence(StrEnum):
    CERTAIN = "certain"
    PROBABLE = "probable"
    DYNAMIC = "dynamic"


class RelationType(StrEnum):
    READS = "reads"
    WRITES = "writes"
    TRIGGERS = "triggers"
    CALLS_SCRIPT = "calls_script"
    CREATES = "creates"
    BELONGS_TO_DEVICE = "belongs_to_device"
    BELONGS_TO_CONFIG_ENTRY = "belongs_to_config_entry"
    BELONGS_TO_AREA = "belongs_to_area"
    USES_BLUEPRINT = "uses_blueprint"
    DISPLAYED_IN = "displayed_in"
    MEMBER_OF = "member_of"
    SOURCE_OF = "source_of"
    DEPENDS_ON = "depends_on"
    REFERENCES = "references"


@dataclass(frozen=True, slots=True)
class Node:
    node_id: str
    node_type: str
    name: str | None = None
    metadata: Mapping[str, Any] = field(
        default_factory=dict,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not self.node_id or not self.node_id.strip():
            raise ValueError("node_id must not be empty")
        if not self.node_type or not self.node_type.strip():
            raise ValueError("node_type must not be empty")
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
        )


@dataclass(frozen=True, slots=True)
class Edge:
    source_node_id: str
    target_node_id: str
    relation_type: RelationType
    source_parser: str
    confidence: Confidence = Confidence.CERTAIN
    source_file: str | None = None
    source_path: str | None = None
    explanation: str | None = None
    metadata: Mapping[str, Any] = field(
        default_factory=dict,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not self.source_node_id or not self.source_node_id.strip():
            raise ValueError("source_node_id must not be empty")
        if not self.target_node_id or not self.target_node_id.strip():
            raise ValueError("target_node_id must not be empty")
        if not self.source_parser or not self.source_parser.strip():
            raise ValueError("source_parser must not be empty")
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
        )
