from __future__ import annotations
from dataclasses import dataclass, field
from ..model import Edge, Node

@dataclass(slots=True)
class ParserResult:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
