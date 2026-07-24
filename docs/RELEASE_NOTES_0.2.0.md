# Entity Dependency Engine v0.2.0

Version 0.2.0 adds the Home Assistant dependency explorer panel while
preserving the complete v0.1.0 report workflow.

## Highlights

- Administrator-only Home Assistant sidebar panel.
- Server-side entity search with total-result counts.
- Vertical layered dependency graph.
- Parents and ancestors above the root.
- Children and descendants below the root.
- One-step parent and child expansion.
- Independent node selection and **Focus here** navigation.
- Navigation history and direct URLs.
- **Center root** and **Reset view** controls.
- Cycle and broken-reference presentation.
- Horizontal and vertical graph scrolling.

## Compatibility

These remain compatible with v0.1.0:

- `entity_dependency_engine.generate_report`
- `sensor.entity_dependency_engine_last_report`
- Existing config entries
- Existing scripts, automations, and dashboards
- Private and optional public report paths
- English and Swedish reports

No manual migration is required.

## Validation

The release has been validated through:

- HACS upgrade from v0.1.0
- Clean HACS installation
- Home Assistant restart testing
- Panel and graph testing
- Existing report workflow testing
- HACS validation
- Hassfest validation
- Python tests
- Frontend syntax validation

Remove private information before attaching logs, reports, or screenshots
to public issues.
