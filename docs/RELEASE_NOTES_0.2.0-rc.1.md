# Entity Dependency Engine v0.2.0-rc.1

This release candidate adds the Home Assistant dependency-explorer panel while preserving the v0.1.0 report workflow.

## Highlights

- Search entities from an administrator-only sidebar panel.
- View parents above and children below the selected root.
- Expand parent and child branches one step at a time.
- Select nodes independently or use **Focus here** to change the root.
- Navigate between previous roots and share direct URLs.
- Center the root or reset expanded branches.
- Identify cycles and broken references.
- Continue using the existing report action and latest-report sensor.

## Compatibility

These remain unchanged:

- `entity_dependency_engine.generate_report`
- `sensor.entity_dependency_engine_last_report`
- `/config/entity_dependency_engine/reports/`
- `/config/www/entity_dependency_engine/`
- `/local/entity_dependency_engine/`

Existing config entries, scripts, automations, dashboards, and saved reports should continue to work without manual migration.

## Testing requested

Please test HACS upgrade, clean installation, restart, entity search, graph layout, branch expansion, history, direct URLs, **Focus here**, **Center root**, **Reset view**, report generation, and latest-report sensor updates.

Remove private information before attaching logs or screenshots.
