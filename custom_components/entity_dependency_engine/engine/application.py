"""Application layer for generating and storing dependency reports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .builder import build_graph
from .reports import build_dependency_report, format_dependency_report
from .reports.readable import format_readable_report, format_summary, normalize_language


@dataclass(frozen=True, slots=True)
class GeneratedReport:
    entity_id: str
    summary: str
    report_text: str
    debug_text: str
    generated: str
    parents: int
    children: int
    ancestors: int
    descendants: int
    broken: int
    build_warnings: int
    private_file: Path
    private_debug_file: Path
    private_latest_file: Path
    public_url: str | None = None
    public_debug_url: str | None = None
    public_latest_url: str | None = None

    def as_response(self, *, include_report_text: bool = True) -> dict[str, object]:
        response: dict[str, object] = {
            "ok": True,
            "entity_id": self.entity_id,
            "summary": self.summary,
            "parents": self.parents,
            "children": self.children,
            "ancestors": self.ancestors,
            "descendants": self.descendants,
            "broken": self.broken,
            "build_warnings": self.build_warnings,
            "generated": self.generated,
            "private_file": str(self.private_file),
            "private_debug_file": str(self.private_debug_file),
            "private_latest_file": str(self.private_latest_file),
        }
        if include_report_text:
            response["report"] = self.report_text
        if self.public_url:
            response["url"] = self.public_url
            response["debug_url"] = self.public_debug_url
            response["latest_url"] = self.public_latest_url
        return response


def generate_report(
    *,
    config_dir: str | Path,
    entity_id: str,
    private_output_dir: str | Path,
    language: str = "en",
    include_structural: bool = False,
    max_depth: int | None = None,
    public_output_dir: str | Path | None = None,
    public_url_prefix: str = "/local/entity_dependency_engine",
) -> GeneratedReport:
    """Build the graph, generate reports and save them atomically."""
    normalized_language = normalize_language(language)
    build = build_graph(config_dir)
    if build.graph.get_node(entity_id) is None:
        raise KeyError(entity_id)

    readable_report = build_dependency_report(
        build.graph,
        entity_id,
        include_structural=include_structural,
        max_depth=max_depth,
    )
    debug_report = build_dependency_report(
        build.graph,
        entity_id,
        include_structural=True,
        max_depth=max_depth,
    )

    generated = datetime.now().astimezone().isoformat(timespec="seconds")
    readable_text = format_readable_report(
        readable_report,
        generated=generated,
        language=normalized_language,
    )
    warning_text = "\n".join(f"  {warning}" for warning in build.warnings)
    debug_text = (
        f"{format_dependency_report(debug_report)}\n\n"
        f"Generated: {generated}\n"
        f"Graph nodes: {build.graph.node_count}\n"
        f"Graph edges: {build.graph.edge_count}\n"
        f"Build warnings: {len(build.warnings)}\n"
    )
    if warning_text:
        debug_text += f"\nBuild warnings:\n{warning_text}\n"

    safe_name = entity_id.replace(".", "_")
    private_dir = Path(private_output_dir)
    private_file = private_dir / f"{safe_name}.txt"
    private_debug_file = private_dir / f"{safe_name}_debug.txt"
    private_latest_file = private_dir / "latest_report.txt"
    _write_atomic(private_file, readable_text)
    _write_atomic(private_debug_file, debug_text)
    _write_atomic(private_latest_file, readable_text)

    public_url = public_debug_url = public_latest_url = None
    if public_output_dir is not None:
        public_dir = Path(public_output_dir)
        _write_atomic(public_dir / f"{safe_name}.txt", readable_text)
        _write_atomic(public_dir / f"{safe_name}_debug.txt", debug_text)
        _write_atomic(public_dir / "latest_report.txt", readable_text)
        prefix = public_url_prefix.rstrip("/")
        public_url = f"{prefix}/{safe_name}.txt"
        public_debug_url = f"{prefix}/{safe_name}_debug.txt"
        public_latest_url = f"{prefix}/latest_report.txt"

    return GeneratedReport(
        entity_id=entity_id,
        summary=format_summary(readable_report, language=normalized_language),
        report_text=readable_text,
        debug_text=debug_text,
        generated=generated,
        parents=len(readable_report.direct_parents),
        children=len(readable_report.direct_children),
        ancestors=len(readable_report.ancestors),
        descendants=len(readable_report.descendants),
        broken=len(readable_report.broken_references),
        build_warnings=len(build.warnings),
        private_file=private_file,
        private_debug_file=private_debug_file,
        private_latest_file=private_latest_file,
        public_url=public_url,
        public_debug_url=public_debug_url,
        public_latest_url=public_latest_url,
    )


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)
