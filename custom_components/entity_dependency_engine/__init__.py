"""The Entity Dependency Engine integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_ENTITY_ID,
    ATTR_INCLUDE_STRUCTURAL,
    ATTR_LANGUAGE,
    ATTR_MAX_DEPTH,
    ATTR_SAVE_PUBLIC_COPY,
    DEFAULT_INCLUDE_STRUCTURAL,
    DEFAULT_SAVE_PUBLIC_COPY,
    DOMAIN,
    SERVICE_GENERATE_REPORT,
    SUPPORTED_LANGUAGES,
)
from .engine.application import generate_report
from .runtime import (
    EntityDependencyEngineRuntimeData,
    ReportSnapshot,
    load_report_snapshot,
)
from .websocket import async_register_websocket_commands

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type EntityDependencyEngineConfigEntry = ConfigEntry[
    EntityDependencyEngineRuntimeData
]

_GENERATE_REPORT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Optional(
            ATTR_INCLUDE_STRUCTURAL, default=DEFAULT_INCLUDE_STRUCTURAL
        ): cv.boolean,
        vol.Optional(ATTR_MAX_DEPTH): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Optional(ATTR_LANGUAGE): vol.In(SUPPORTED_LANGUAGES),
        vol.Optional(
            ATTR_SAVE_PUBLIC_COPY, default=DEFAULT_SAVE_PUBLIC_COPY
        ): cv.boolean,
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Entity Dependency Engine and register its action."""
    async_register_websocket_commands(hass)

    async def async_generate_report(call: ServiceCall) -> ServiceResponse:
        loaded_entries = [
            entry
            for entry in hass.config_entries.async_entries(DOMAIN)
            if entry.state is ConfigEntryState.LOADED
        ]
        if not loaded_entries:
            raise ServiceValidationError(
                "Entity Dependency Engine is not configured or loaded"
            )

        entry: EntityDependencyEngineConfigEntry = loaded_entries[0]
        entity_id = call.data[ATTR_ENTITY_ID]
        language = call.data.get(ATTR_LANGUAGE) or hass.config.language or "en"
        save_public_copy = call.data[ATTR_SAVE_PUBLIC_COPY]
        private_output_dir = hass.config.path(DOMAIN, "reports")
        public_output_dir = (
            hass.config.path("www", DOMAIN) if save_public_copy else None
        )

        try:
            result = await hass.async_add_executor_job(
                lambda: generate_report(
                    config_dir=hass.config.config_dir,
                    entity_id=entity_id,
                    private_output_dir=private_output_dir,
                    language=language,
                    include_structural=call.data[ATTR_INCLUDE_STRUCTURAL],
                    max_depth=call.data.get(ATTR_MAX_DEPTH),
                    public_output_dir=public_output_dir,
                )
            )
        except KeyError as err:
            raise ServiceValidationError(
                f"Entity {entity_id!r} was not found in the dependency graph"
            ) from err
        except (OSError, RuntimeError, ValueError) as err:
            _LOGGER.exception(
                "Could not generate a dependency report for %s", entity_id
            )
            raise ServiceValidationError(
                f"Could not generate the dependency report: {err}"
            ) from err

        entry.runtime_data.async_set_report(
            ReportSnapshot.from_generated_report(result)
        )

        if not call.return_response:
            return None
        return result.as_response(include_report_text=True)

    hass.services.async_register(
        DOMAIN,
        SERVICE_GENERATE_REPORT,
        async_generate_report,
        schema=_GENERATE_REPORT_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: EntityDependencyEngineConfigEntry
) -> bool:
    """Set up Entity Dependency Engine from a config entry."""
    latest_report_file = hass.config.path(DOMAIN, "reports", "latest_report.txt")
    report = await hass.async_add_executor_job(
        load_report_snapshot, latest_report_file
    )
    entry.runtime_data = EntityDependencyEngineRuntimeData(report=report)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: EntityDependencyEngineConfigEntry
) -> bool:
    """Unload the config entry and its platforms."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
