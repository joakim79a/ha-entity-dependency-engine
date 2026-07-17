"""Static entity-reference extraction from Home Assistant Jinja templates."""

from __future__ import annotations

import re
from dataclasses import dataclass


ENTITY_ID_CORE = r"[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z0-9_]+"

CALL_PATTERN = re.compile(
    rf"""
    (?:
        states
        |state_attr
        |is_state
        |is_state_attr
        |expand
        |has_value
        |device_attr
    )
    \s*\(\s*
    (?P<quote>['"])
    (?P<entity>{ENTITY_ID_CORE})
    (?P=quote)
    """,
    re.VERBOSE,
)

DIRECT_STATES_PATTERN = re.compile(
    rf"\bstates\.(?P<domain>[a-zA-Z_][a-zA-Z0-9_]*)\."
    rf"(?P<object>[a-zA-Z0-9_]+)\b"
)

# A plain entity id must be a complete token, not a fragment of a longer
# dotted expression such as:
#   states.sensor.pulse_elpris.state
PLAIN_ENTITY_PATTERN = re.compile(
    rf"(?<![a-zA-Z0-9_.])(?P<entity>{ENTITY_ID_CORE})(?![a-zA-Z0-9_.])"
)


@dataclass(frozen=True, slots=True)
class TemplateReferences:
    """References extracted from one template string."""

    certain: frozenset[str]
    probable: frozenset[str]


def extract_template_references(template: str) -> TemplateReferences:
    """Extract static entity references from Jinja text.

    `certain` contains references found in recognized HA/Jinja access forms.
    `probable` contains complete plain entity-id tokens found elsewhere.
    """
    certain: set[str] = set()

    for match in CALL_PATTERN.finditer(template):
        certain.add(match.group("entity"))

    for match in DIRECT_STATES_PATTERN.finditer(template):
        certain.add(f"{match.group('domain')}.{match.group('object')}")

    probable = {
        match.group("entity")
        for match in PLAIN_ENTITY_PATTERN.finditer(template)
        if match.group("entity") not in certain
    }

    return TemplateReferences(
        certain=frozenset(certain),
        probable=frozenset(probable),
    )
