"""Constants for Entity Dependency Engine."""

DOMAIN = "entity_dependency_engine"
NAME = "Entity Dependency Engine"

SERVICE_GENERATE_REPORT = "generate_report"

ATTR_ENTITY_ID = "entity_id"
ATTR_INCLUDE_STRUCTURAL = "include_structural"
ATTR_LANGUAGE = "language"
ATTR_MAX_DEPTH = "max_depth"
ATTR_SAVE_PUBLIC_COPY = "save_public_copy"

DEFAULT_INCLUDE_STRUCTURAL = False
DEFAULT_SAVE_PUBLIC_COPY = False
SUPPORTED_LANGUAGES = {"en", "sv"}

WS_SEARCH_ENTITIES = "entity_dependency_engine/search_entities"
WS_GET_GRAPH = "entity_dependency_engine/get_graph"
WS_EXPAND_NODE = "entity_dependency_engine/expand_node"

DATA_PANEL_GRAPH_CACHE = "entity_dependency_engine_panel_graph_cache"
DATA_WEBSOCKET_REGISTERED = "entity_dependency_engine_websocket_registered"
