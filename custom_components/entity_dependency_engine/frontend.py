"""Register the Entity Dependency Engine frontend panel."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, NAME

PANEL_COMPONENT_NAME = "entity-dependency-engine"
PANEL_URL_PATH = "entity-dependency-engine"
PANEL_TITLE = NAME
PANEL_ICON = "mdi:graph"

FRONTEND_ROOT = Path(__file__).parent / "frontend"
FRONTEND_STATIC_URL = f"/{DOMAIN}_frontend"
FRONTEND_MODULE_URL = (
    f"{FRONTEND_STATIC_URL}/entity-dependency-panel.js?v=0.2.0-alpha.5"
)

DATA_FRONTEND_STATIC_REGISTERED = f"{DOMAIN}_frontend_static_registered"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Register the panel module, static files, and sidebar entry."""
    if not hass.data.get(DATA_FRONTEND_STATIC_REGISTERED):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    FRONTEND_STATIC_URL,
                    str(FRONTEND_ROOT),
                    cache_headers=False,
                )
            ]
        )
        hass.data[DATA_FRONTEND_STATIC_REGISTERED] = True

    frontend.add_extra_js_url(hass, FRONTEND_MODULE_URL)

    if not frontend.async_panel_exists(hass, PANEL_URL_PATH):
        frontend.async_register_built_in_panel(
            hass,
            PANEL_COMPONENT_NAME,
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON,
            sidebar_default_visible=True,
            frontend_url_path=PANEL_URL_PATH,
            config={"version": "0.2.0-alpha.5"},
            require_admin=True,
        )


@callback
def async_unregister_frontend(hass: HomeAssistant) -> None:
    """Remove the sidebar panel and module registration on unload."""
    if frontend.async_panel_exists(hass, PANEL_URL_PATH):
        frontend.async_remove_panel(hass, PANEL_URL_PATH)

    frontend.remove_extra_js_url(hass, FRONTEND_MODULE_URL)
