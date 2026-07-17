"""Runtime state shared by Entity Dependency Engine platforms."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.core import callback

if TYPE_CHECKING:
    from .engine.application import GeneratedReport


@dataclass(frozen=True, slots=True)
class ReportSnapshot:
    """The latest generated dependency report exposed to Home Assistant."""

    generated: str | None = None
    report: str = ""
    entity_id: str | None = None
    summary: str | None = None
    parents: int | None = None
    children: int | None = None
    ancestors: int | None = None
    descendants: int | None = None
    broken: int | None = None
    build_warnings: int | None = None
    private_file: str | None = None
    private_debug_file: str | None = None
    url: str | None = None
    debug_url: str | None = None

    @classmethod
    def from_generated_report(cls, result: GeneratedReport) -> ReportSnapshot:
        """Create a snapshot from a newly generated report."""
        return cls(
            generated=result.generated,
            report=result.report_text,
            entity_id=result.entity_id,
            summary=result.summary,
            parents=result.parents,
            children=result.children,
            ancestors=result.ancestors,
            descendants=result.descendants,
            broken=result.broken,
            build_warnings=result.build_warnings,
            private_file=str(result.private_file),
            private_debug_file=str(result.private_debug_file),
            url=result.public_url,
            debug_url=result.public_debug_url,
        )

    def as_attributes(self) -> dict[str, Any]:
        """Return state attributes while omitting unavailable values."""
        attributes: dict[str, Any] = {"report": self.report}
        optional_values = {
            "entity_id": self.entity_id,
            "summary": self.summary,
            "parents": self.parents,
            "children": self.children,
            "ancestors": self.ancestors,
            "descendants": self.descendants,
            "broken": self.broken,
            "build_warnings": self.build_warnings,
            "private_file": self.private_file,
            "private_debug_file": self.private_debug_file,
            "url": self.url,
            "debug_url": self.debug_url,
        }
        attributes.update(
            {key: value for key, value in optional_values.items() if value is not None}
        )
        return attributes


@dataclass(slots=True)
class EntityDependencyEngineRuntimeData:
    """Mutable runtime data owned by the config entry."""

    report: ReportSnapshot = field(default_factory=ReportSnapshot)
    _listeners: set[Callable[[], None]] = field(default_factory=set)

    @callback
    def async_set_report(self, report: ReportSnapshot) -> None:
        """Store a report and notify push-based entities."""
        self.report = report
        for listener in tuple(self._listeners):
            listener()

    @callback
    def async_subscribe(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to report updates."""
        self._listeners.add(listener)

        @callback
        def unsubscribe() -> None:
            self._listeners.discard(listener)

        return unsubscribe


def load_report_snapshot(report_file: str | Path) -> ReportSnapshot:
    """Load the latest report from disk during config-entry setup."""
    path = Path(report_file)
    if not path.is_file():
        return ReportSnapshot()

    report = path.read_text(encoding="utf-8")
    generated = datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(
        timespec="seconds"
    )
    return ReportSnapshot(generated=generated, report=report)
