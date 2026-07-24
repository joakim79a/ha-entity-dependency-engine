# Changelog

All notable changes are documented here. The project follows semantic versioning for Home Assistant releases.

## [Unreleased]

### Planned

- Add a user-configurable report storage location while preserving the current default.

## [0.2.0] - 2026-07-24

### Added

- Stable administrator-only Home Assistant sidebar panel.
- Server-side entity search and vertical dependency graph.
- Parent and child branch expansion.
- Root navigation, history, direct URLs, centering, and reset controls.
- Cycle and broken-reference presentation.

### Compatibility

- Preserved the v0.1.0 report action and latest-report sensor.
- Preserved report paths, config entries, scripts, automations,
  dashboards, and report languages.
- No manual migration is required.

### Validation

- Validated HACS upgrade from v0.1.0.
- Validated clean HACS installation.
- Passed HACS, Hassfest, Python, and frontend validation.

## [0.2.0-rc.1] - 2026-07-23

### Added

- Administrator-only Home Assistant sidebar panel.
- Entity search with total-result counts.
- Vertical layered dependency graph.
- Parents and ancestors above the root; children and descendants below it.
- One-step parent and child expansion.
- Root focus, node selection, history, direct URLs, centering, and view reset.
- Vertical and horizontal graph scrolling.
- Directional SVG relation lines.
- Cycle and broken-reference presentation.
- Admin-protected WebSocket commands for search, graph retrieval, and expansion.
- Frontend, API, expansion, layout, and v0.1 compatibility tests.

### Changed

- Replaced the early three-column panel with a vertical layered graph.
- Improved search focus, result scrolling, and stale-response handling.
- Split graph layout into a separate frontend module.
- Expanded English GitHub and release documentation.

### Compatibility

- Preserved `entity_dependency_engine.generate_report`.
- Preserved `sensor.entity_dependency_engine_last_report`.
- Preserved report paths, optional `/local` URLs, config entries, scripts, dashboards, and report languages.
- No manual migration is expected from v0.1.0.

## [0.1.0] - 2026-07-17

### Added

- First public HACS release.
- Config flow, report action, and latest-report sensor.
- Recursive dependency analysis and helper parsers.
- Automation and script reference analysis.
- Broken-reference reporting.
- English and Swedish translations and reports.
- Private reports and optional public copies.
- HACS, Hassfest, and unit-test validation.
