"""Pytest setup for the vendored pure engine package."""

from pathlib import Path
import sys

INTEGRATION_DIR = (
    Path(__file__).parent / "custom_components" / "entity_dependency_engine"
)
sys.path.insert(0, str(INTEGRATION_DIR))
