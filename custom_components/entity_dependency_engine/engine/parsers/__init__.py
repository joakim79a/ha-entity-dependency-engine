"""Data-source parsers for Home Assistant."""

from .automations import parse_automation_relations
from .base import ParserResult
from .config_entries import (
    build_device_config_entry_edges,
    build_entity_config_entry_edges,
    parse_config_entries,
)
from .derivative import parse_derivative_relations
from .device_registry import (
    build_entity_device_edges,
    parse_device_registry,
)
from .entity_registry import parse_entity_registry
from .group import parse_group_relations
from .gui_templates import parse_gui_template_relations
from .history_stats import parse_history_stats_relations
from .integration_sensor import parse_integration_relations
from .min_max import parse_min_max_relations
from .scripts import parse_script_relations
from .switch_as_x import parse_switch_as_x_relations
from .threshold import parse_threshold_relations
from .utility_meter import parse_utility_meter_relations

__all__ = [
    "ParserResult",
    "build_device_config_entry_edges",
    "build_entity_config_entry_edges",
    "build_entity_device_edges",
    "parse_automation_relations",
    "parse_config_entries",
    "parse_derivative_relations",
    "parse_device_registry",
    "parse_entity_registry",
    "parse_group_relations",
    "parse_gui_template_relations",
    "parse_history_stats_relations",
    "parse_integration_relations",
    "parse_min_max_relations",
    "parse_script_relations",
    "parse_switch_as_x_relations",
    "parse_threshold_relations",
    "parse_utility_meter_relations",
]
