"""Localized human-readable dependency report formatting."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .dependency import DependencyReport

SUPPORTED_LANGUAGES = {"en", "sv"}

_TEXT = {
    "en": {
        "title": "ENTITY RELATIONSHIPS",
        "root": "Root",
        "name": "Name",
        "none": "None",
        "level": "Level",
        "parents_title": "Direct parents - these affect the root entity",
        "children_title": "Direct children - these are directly affected by the root entity",
        "ancestors_title": "All ancestors - the complete upstream chain",
        "descendants_title": "All descendants - the complete downstream chain",
        "broken_title": "Broken references in this chain",
        "summary_title": "SUMMARY",
        "parents": "Direct parents",
        "children": "Direct children",
        "ancestors": "All ancestors",
        "descendants": "All descendants",
        "broken": "Broken references",
        "generated": "Generated",
        "debug_note": "A technical raw report is available in the corresponding *_debug.txt file.",
        "relation": "relation",
        "summary": (
            "{entity_id}: {parents} direct parents, {children} direct children, "
            "{ancestors} ancestors and {descendants} descendants."
        ),
    },
    "sv": {
        "title": "ENTITETSRELATIONER",
        "root": "Rot",
        "name": "Namn",
        "none": "Inga",
        "level": "Nivå",
        "parents_title": "Direkta föräldrar - detta påverkar rotentiteten",
        "children_title": "Direkta barn - detta påverkas direkt av rotentiteten",
        "ancestors_title": "Alla förfäder - hela kedjan uppströms",
        "descendants_title": "Alla ättlingar - hela kedjan nedströms",
        "broken_title": "Brutna referenser i denna kedja",
        "summary_title": "SAMMANFATTNING",
        "parents": "Direkta föräldrar",
        "children": "Direkta barn",
        "ancestors": "Alla förfäder",
        "descendants": "Alla ättlingar",
        "broken": "Brutna referenser",
        "generated": "Skapad",
        "debug_note": "En teknisk rårapport finns i motsvarande *_debug.txt-fil.",
        "relation": "relation",
        "summary": (
            "{entity_id}: {parents} direkta föräldrar, {children} direkta barn, "
            "{ancestors} förfäder och {descendants} ättlingar."
        ),
    },
}


def normalize_language(language: str | None) -> str:
    """Return a supported two-letter language code, falling back to English."""
    if not language:
        return "en"
    normalized = language.lower().replace("_", "-").split("-", maxsplit=1)[0]
    return normalized if normalized in SUPPORTED_LANGUAGES else "en"


def format_readable_report(
    report: DependencyReport,
    *,
    generated: str,
    language: str = "en",
) -> str:
    """Format a report for humans in English or Swedish."""
    text = _TEXT[normalize_language(language)]
    lines = [
        text["title"],
        "=" * len(text["title"]),
        f'{text["root"]}: {report.root.node_id}',
        f'{text["name"]}: {report.root.name or "-"}',
    ]

    lines.extend(_format_direct(text["parents_title"], report.direct_parents, text))
    lines.extend(_format_direct(text["children_title"], report.direct_children, text))
    lines.extend(_format_recursive(text["ancestors_title"], report.ancestors, text))
    lines.extend(_format_recursive(text["descendants_title"], report.descendants, text))
    lines.extend(_format_direct(text["broken_title"], report.broken_references, text))

    lines.extend([
        "",
        text["summary_title"],
        "-" * len(text["summary_title"]),
        f'{text["parents"]}: {len(report.direct_parents)}',
        f'{text["children"]}: {len(report.direct_children)}',
        f'{text["ancestors"]}: {len(report.ancestors)}',
        f'{text["descendants"]}: {len(report.descendants)}',
        f'{text["broken"]}: {len(report.broken_references)}',
        f'{text["generated"]}: {generated}',
        "",
        text["debug_note"],
    ])
    return "\n".join(lines) + "\n"


def format_summary(report: DependencyReport, *, language: str = "en") -> str:
    """Return a one-line localized report summary."""
    text = _TEXT[normalize_language(language)]
    return text["summary"].format(
        entity_id=report.root.node_id,
        parents=len(report.direct_parents),
        children=len(report.direct_children),
        ancestors=len(report.ancestors),
        descendants=len(report.descendants),
    )


def _display_name(item: Any) -> str:
    node_id = item.node.node_id
    name = item.node.name
    return f"{node_id} ({name})" if name and name != node_id else node_id


def _relation_summary(item: Any, fallback: str) -> str:
    names = sorted({edge.relation_type.value for edge in item.edges})
    return ", ".join(names) if names else fallback


def _format_direct(title: str, items: Iterable[Any], text: dict[str, str]) -> list[str]:
    values = tuple(items)
    lines = ["", title, "-" * len(title)]
    if not values:
        lines.append(text["none"])
        return lines
    for item in values:
        lines.append(
            f'- {_display_name(item)} [{_relation_summary(item, text["relation"])}]'
        )
    return lines


def _format_recursive(title: str, items: Iterable[Any], text: dict[str, str]) -> list[str]:
    values = tuple(items)
    lines = ["", title, "-" * len(title)]
    if not values:
        lines.append(text["none"])
        return lines
    grouped: dict[int, list[Any]] = {}
    for item in values:
        grouped.setdefault(item.depth, []).append(item)
    for depth in sorted(grouped):
        lines.append(f'{text["level"]} {depth}:')
        for item in sorted(grouped[depth], key=lambda value: value.node.node_id):
            lines.append(f"  - {_display_name(item)}")
    return lines
