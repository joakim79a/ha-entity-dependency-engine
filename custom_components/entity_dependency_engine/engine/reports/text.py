"""Plain-text formatting for dependency reports."""

from __future__ import annotations

from .dependency import (
    DependencyReport,
    RelatedNode,
)


def format_dependency_report(report: DependencyReport) -> str:
    lines: list[str] = []

    lines.append("Entity Dependency Report")
    lines.append("=" * 24)
    lines.append(f"Root: {report.root.node_id}")
    lines.append(f"Name: {report.root.name or '-'}")
    lines.append(f"Type: {report.root.node_type}")

    lines.extend(_section("Direct parents", report.direct_parents))
    lines.extend(_section("Direct children", report.direct_children))
    lines.extend(_section("All ancestors", report.ancestors))
    lines.extend(_section("All descendants", report.descendants))
    lines.extend(_section("Broken references", report.broken_references))

    lines.append("")
    lines.append(
        "Summary: "
        f"parents={len(report.direct_parents)}, "
        f"children={len(report.direct_children)}, "
        f"ancestors={len(report.ancestors)}, "
        f"descendants={len(report.descendants)}, "
        f"broken={len(report.broken_references)}"
    )

    return "\n".join(lines)


def _section(title: str, items: tuple[RelatedNode, ...]) -> list[str]:
    lines = ["", f"{title}:"]

    if not items:
        lines.append("  none")
        return lines

    for item in items:
        lines.append(
            f"  [depth {item.depth}] "
            f"{item.node.node_id}"
            + (f" ({item.node.name})" if item.node.name else "")
        )

        for edge in item.edges:
            lines.append(
                "      "
                f"{edge.relation_type.value} | "
                f"{edge.source_parser} | "
                f"{edge.confidence.value}"
                + (
                    f" | {edge.source_path}"
                    if edge.source_path
                    else ""
                )
            )

    return lines
