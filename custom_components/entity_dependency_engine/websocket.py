"""Admin-only WebSocket API for the visual dependency panel."""

from __future__ import annotations

from functools import partial
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    ATTR_FRIENDLY_NAME,
    ATTR_ICON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import (
    area_registry as ar,
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)

from .const import (
    DATA_PANEL_GRAPH_CACHE,
    DATA_WEBSOCKET_REGISTERED,
    DOMAIN,
    WS_EXPAND_NODE,
    WS_GET_GRAPH,
    WS_SEARCH_ENTITIES,
)
from .engine.builder import BuildResult
from .engine.panel_graph import (
    ABSOLUTE_MAX_NODES,
    DEFAULT_MAX_NODES,
    VALID_SCOPES,
    serialize_panel_graph,
)
from .engine.panel_api import PanelGraphCache, search_graph_entities
from .engine.panel_expansion import (
    VALID_EXPANSION_DIRECTIONS,
    expand_panel_graph,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_SEARCH_LIMIT = 50
MAX_SEARCH_LIMIT = 200


@callback
def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register panel WebSocket commands once per Home Assistant process."""
    if hass.data.get(DATA_WEBSOCKET_REGISTERED):
        return

    hass.data.setdefault(DATA_PANEL_GRAPH_CACHE, PanelGraphCache())
    websocket_api.async_register_command(hass, websocket_search_entities)
    websocket_api.async_register_command(hass, websocket_get_graph)
    websocket_api.async_register_command(hass, websocket_expand_node)
    hass.data[DATA_WEBSOCKET_REGISTERED] = True


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_SEARCH_ENTITIES,
        vol.Optional("query", default=""): cv.string,
        vol.Optional("limit", default=DEFAULT_SEARCH_LIMIT): vol.All(
            vol.Coerce(int),
            vol.Range(min=1, max=MAX_SEARCH_LIMIT),
        ),
        vol.Optional("refresh", default=False): cv.boolean,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_search_entities(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Search graph entities by friendly name, entity ID, or context."""
    if not _integration_loaded(hass):
        connection.send_error(
            msg["id"],
            "not_loaded",
            "Entity Dependency Engine is not configured or loaded",
        )
        return

    try:
        build = await _async_get_build(
            hass,
            refresh=msg["refresh"],
        )
        runtime_entities = _build_runtime_entities(hass, build)
        result = await hass.async_add_executor_job(
            partial(
                search_graph_entities,
                build.graph,
                runtime_entities=runtime_entities,
                query=msg["query"],
                limit=msg["limit"],
            )
        )
    except (OSError, RuntimeError, ValueError) as err:
        _LOGGER.exception("Could not search dependency graph entities")
        connection.send_error(msg["id"], "graph_build_failed", str(err))
        return

    result["build_warning_count"] = len(build.warnings)
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_GET_GRAPH,
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("scope", default="direct"): vol.In(VALID_SCOPES),
        vol.Optional("max_nodes", default=DEFAULT_MAX_NODES): vol.All(
            vol.Coerce(int),
            vol.Range(min=1, max=ABSOLUTE_MAX_NODES),
        ),
        vol.Optional("include_structural", default=False): cv.boolean,
        vol.Optional("refresh", default=False): cv.boolean,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_get_graph(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return a serialized dependency graph for the selected entity."""
    if not _integration_loaded(hass):
        connection.send_error(
            msg["id"],
            "not_loaded",
            "Entity Dependency Engine is not configured or loaded",
        )
        return

    entity_id = msg["entity_id"]

    try:
        build = await _async_get_build(
            hass,
            refresh=msg["refresh"],
        )
        if build.graph.get_node(entity_id) is None:
            connection.send_error(
                msg["id"],
                websocket_api.ERR_NOT_FOUND,
                f"Entity {entity_id!r} was not found in the dependency graph",
            )
            return

        runtime_entities = _build_runtime_entities(hass, build)
        payload = await hass.async_add_executor_job(
            partial(
                serialize_panel_graph,
                build.graph,
                entity_id,
                scope=msg["scope"],
                max_nodes=msg["max_nodes"],
                include_structural=msg["include_structural"],
                runtime_entities=runtime_entities,
                warnings=build.warnings,
            )
        )
    except (OSError, RuntimeError, ValueError) as err:
        _LOGGER.exception(
            "Could not build panel graph for %s",
            entity_id,
        )
        connection.send_error(msg["id"], "graph_build_failed", str(err))
        return

    connection.send_result(msg["id"], payload)


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_EXPAND_NODE,
        vol.Required("root_id"): cv.entity_id,
        vol.Required("node_id"): cv.string,
        vol.Required("direction"): vol.In(VALID_EXPANSION_DIRECTIONS),
        vol.Required("visible_node_ids"): vol.All(
            [cv.string],
            vol.Length(min=1, max=ABSOLUTE_MAX_NODES),
        ),
        vol.Optional("max_nodes", default=DEFAULT_MAX_NODES): vol.All(
            vol.Coerce(int),
            vol.Range(min=1, max=ABSOLUTE_MAX_NODES),
        ),
        vol.Optional("include_structural", default=False): cv.boolean,
        vol.Optional("refresh", default=False): cv.boolean,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_expand_node(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Expand one visible graph node without changing the graph root."""
    if not _integration_loaded(hass):
        connection.send_error(
            msg["id"],
            "not_loaded",
            "Entity Dependency Engine is not configured or loaded",
        )
        return

    root_id = msg["root_id"]
    node_id = msg["node_id"]

    try:
        build = await _async_get_build(
            hass,
            refresh=msg["refresh"],
        )
        missing = [
            candidate
            for candidate in (root_id, node_id)
            if build.graph.get_node(candidate) is None
        ]
        if missing:
            connection.send_error(
                msg["id"],
                websocket_api.ERR_NOT_FOUND,
                "Graph node(s) not found: " + ", ".join(missing),
            )
            return

        runtime_entities = _build_runtime_entities(hass, build)
        payload = await hass.async_add_executor_job(
            partial(
                expand_panel_graph,
                build.graph,
                root_id,
                node_id,
                direction=msg["direction"],
                visible_node_ids=msg["visible_node_ids"],
                max_nodes=msg["max_nodes"],
                include_structural=msg["include_structural"],
                runtime_entities=runtime_entities,
                warnings=build.warnings,
            )
        )
    except (KeyError, OSError, RuntimeError, ValueError) as err:
        _LOGGER.exception(
            "Could not expand panel graph node %s",
            node_id,
        )
        connection.send_error(msg["id"], "graph_expand_failed", str(err))
        return

    connection.send_result(msg["id"], payload)


async def _async_get_build(
    hass: HomeAssistant,
    *,
    refresh: bool,
) -> BuildResult:
    cache = _get_cache(hass)
    return await hass.async_add_executor_job(
        partial(
            cache.get,
            hass.config.config_dir,
            refresh=refresh,
        )
    )


@callback
def _get_cache(hass: HomeAssistant) -> PanelGraphCache:
    cache = hass.data.get(DATA_PANEL_GRAPH_CACHE)
    if isinstance(cache, PanelGraphCache):
        return cache

    cache = PanelGraphCache()
    hass.data[DATA_PANEL_GRAPH_CACHE] = cache
    return cache


@callback
def _integration_loaded(hass: HomeAssistant) -> bool:
    return any(
        entry.state is ConfigEntryState.LOADED
        for entry in hass.config_entries.async_entries(DOMAIN)
    )


@callback
def _build_runtime_entities(
    hass: HomeAssistant,
    build: BuildResult,
) -> dict[str, dict[str, Any]]:
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    area_registry = ar.async_get(hass)
    runtime_entities: dict[str, dict[str, Any]] = {}

    for node in build.graph.iter_nodes():
        entity_id = node.node_id
        if "." not in entity_id:
            continue

        state = hass.states.get(entity_id)
        registry_entry = entity_registry.async_get(entity_id)

        device = None
        if registry_entry is not None and registry_entry.device_id:
            device = device_registry.async_get(registry_entry.device_id)

        area_id = None
        if registry_entry is not None and registry_entry.area_id:
            area_id = registry_entry.area_id
        elif device is not None and device.area_id:
            area_id = device.area_id

        area = (
            area_registry.async_get_area(area_id)
            if area_id is not None
            else None
        )

        friendly_name = None
        icon = None
        current_state = None
        if state is not None:
            friendly_name = state.attributes.get(ATTR_FRIENDLY_NAME)
            icon = state.attributes.get(ATTR_ICON)
            current_state = state.state

        registry_name = None
        platform = None
        if registry_entry is not None:
            registry_name = registry_entry.name or registry_entry.original_name
            platform = registry_entry.platform
            icon = icon or registry_entry.icon or registry_entry.original_icon

        runtime_entities[entity_id] = {
            "friendly_name": friendly_name,
            "registry_name": registry_name,
            "state": current_state,
            "state_display": current_state,
            "available": state is not None
            and current_state != STATE_UNAVAILABLE,
            "icon": icon,
            "device_name": (
                device.name_by_user or device.name
                if device is not None
                else None
            ),
            "area_name": area.name if area is not None else None,
            "integration": platform,
        }

    return runtime_entities
