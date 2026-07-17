"""Sensor platform for Entity Dependency Engine."""

from __future__ import annotations

from typing import Any, override

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EntityDependencyEngineConfigEntry
from .runtime import EntityDependencyEngineRuntimeData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EntityDependencyEngineConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the latest-report sensor."""
    async_add_entities([EntityDependencyLastReportSensor(entry.runtime_data)])


class EntityDependencyLastReportSensor(SensorEntity):
    """Expose the latest dependency report without polling."""

    _attr_has_entity_name = True
    _attr_translation_key = "last_report"
    _attr_unique_id = "last_report"
    _attr_should_poll = False
    _attr_icon = "mdi:file-tree"
    _unrecorded_attributes = frozenset({"report"})

    def __init__(self, runtime_data: EntityDependencyEngineRuntimeData) -> None:
        """Initialize the report sensor."""
        self._runtime_data = runtime_data

    @property
    @override
    def suggested_object_id(self) -> str:
        """Use a stable entity id independent of the UI language."""
        return "entity_dependency_engine_last_report"

    @property
    @override
    def native_value(self) -> str | None:
        """Return the generation timestamp as the sensor state."""
        return self._runtime_data.report.generated

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the report and its summary metadata."""
        return self._runtime_data.report.as_attributes()

    async def async_added_to_hass(self) -> None:
        """Subscribe after the entity has been added to Home Assistant."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._runtime_data.async_subscribe(self._async_report_updated)
        )

    @callback
    def _async_report_updated(self) -> None:
        """Write a pushed report update to the state machine."""
        self.async_write_ha_state()
