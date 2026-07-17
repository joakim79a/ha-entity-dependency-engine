"""Report generation for Entity Dependency Engine."""

from .dependency import DependencyReport, RelatedNode, build_dependency_report
from .text import format_dependency_report

__all__ = [
    "DependencyReport",
    "RelatedNode",
    "build_dependency_report",
    "format_dependency_report",
]

from .readable import format_readable_report, format_summary, normalize_language

__all__ += [
    "format_readable_report",
    "format_summary",
    "normalize_language",
]
