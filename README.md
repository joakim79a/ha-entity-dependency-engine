# Entity Dependency Engine

[![Validate](https://github.com/joakim79a/ha-entity-dependency-engine/actions/workflows/validate.yml/badge.svg)](https://github.com/joakim79a/ha-entity-dependency-engine/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/joakim79a/ha-entity-dependency-engine?include_prereleases)](https://github.com/joakim79a/ha-entity-dependency-engine/releases)
[![License](https://img.shields.io/github/license/joakim79a/ha-entity-dependency-engine)](LICENSE)

Entity Dependency Engine is a read-only Home Assistant custom integration for exploring and reporting entity dependencies before you rename, disable, replace, or remove an entity.

> **Release candidate:** `v0.2.0-rc.1` is intended for final upgrade and clean-install validation before stable `v0.2.0`.

## Highlights

- Administrator-only Home Assistant sidebar panel
- Entity search with server-side filtering
- Vertical dependency graph with parents above and children below the root
- One-step parent and child expansion
- Navigation history, direct links, root centering, and view reset
- Cycle and broken-reference indicators
- Recursive reports in English or Swedish
- Backward-compatible report action and latest-report sensor
- Private report storage by default

## Screenshots

![Dependency graph](docs/images/panel-overview.jpg)

![Expanded dependency graph](docs/images/panel-expanded-tree.jpg)

![Entity search](docs/images/panel-search.jpg)

### Additional panel view

![Additional dependency graph view](docs/images/panel-details.jpg)

## Requirements

- Home Assistant `2026.6.0` or newer
- HACS for the recommended installation method
- An administrator account for the sidebar panel

## Installation with HACS

1. Open HACS.
2. Open **Custom repositories**.
3. Add `https://github.com/joakim79a/ha-entity-dependency-engine` as an **Integration**.
4. Search for **Entity Dependency Engine** and download it.
5. Restart Home Assistant.
6. Open **Settings > Devices & services > Add integration**.
7. Add **Entity Dependency Engine**.

For release-candidate testing, enable prereleases for this repository and install `v0.2.0-rc.1`.

## Sidebar panel

The panel lets administrators search entities, inspect a vertical dependency graph, expand branches, select nodes, use **Focus here**, navigate between previous roots, copy a direct URL, center the root, reset the view, and open Home Assistant's more-info dialog.

The panel is read-only and does not modify Home Assistant entities or configuration.

## Generate a report

```yaml
action: entity_dependency_engine.generate_report
data:
  entity_id: sensor.example
  language: en
  include_structural: false
  save_public_copy: false
response_variable: dependency_report
```

| Option | Description |
|---|---|
| `entity_id` | Entity to analyse |
| `language` | `en` or `sv` |
| `include_structural` | Include device and config-entry relations |
| `save_public_copy` | Also save files below `/config/www` |
| `max_depth` | Optional recursive depth limit |

The action also updates `sensor.entity_dependency_engine_last_report`.

## Report storage

Private reports:

```text
/config/entity_dependency_engine/reports/
```

Optional public copies:

```text
/config/www/entity_dependency_engine/
/local/entity_dependency_engine/
```

Public copies are disabled by default. Reports can contain sensitive names and configuration details.

## Compatibility with v0.1.0

Version v0.2.0 is designed as an additive upgrade. These remain compatible:

- `entity_dependency_engine.generate_report`
- `sensor.entity_dependency_engine_last_report`
- existing config entries, scripts, automations, and dashboards
- private and optional public report paths
- English and Swedish reports

No manual migration is expected. See [Upgrading](docs/UPGRADING.md).

## Languages

English is used for code, logs, GitHub documentation, and panel text. Swedish Home Assistant translations and Swedish reports are included.

## Issues and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening an issue and [SECURITY.md](SECURITY.md) before reporting a vulnerability. Remove private names, addresses, tokens, locations, and sensitive configuration from logs and screenshots.

## Support

[Buy me a coffee](https://buymeacoffee.com/joakim79a)

## License

MIT


