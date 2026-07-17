# Entity Dependency Engine

Entity Dependency Engine is a read-only Home Assistant custom integration that builds a directed dependency graph for a selected entity. It can trace direct and recursive upstream and downstream relationships before you rename, disable, replace, or remove an entity.

> Development status: packaging preview. The analysis engine is functional and covered by unit tests, but the integration still needs runtime testing on a clean Home Assistant installation before the first public release.

## Current capabilities

The engine currently analyses:

- Home Assistant entity, device, and config-entry registries
- GUI-created template entities
- Utility Meter, Derivative, Min/Max, History Stats, Integration, Threshold, Group, and Switch-as-X helpers
- Automations and scripts
- Direct parents and children
- Recursive ancestors and descendants
- Broken or unresolved entity references
- Structural relations to devices and config entries

## Installation for development

1. Copy `custom_components/entity_dependency_engine` to `/config/custom_components/entity_dependency_engine`.
2. Restart Home Assistant.
3. Open **Settings > Devices & services > Add integration**.
4. Search for **Entity Dependency Engine** and add it.

For HACS installation, add `https://github.com/joakim79a/ha-entity-dependency-engine` as a custom integration repository in HACS.

## Generate a report

Call the action:

```yaml
action: entity_dependency_engine.generate_report
data:
  entity_id: sensor.example
  language: en
  include_structural: false
  save_public_copy: false
response_variable: dependency_report
```

The action returns counts, a summary, and the readable report when a response is requested. It also updates the native push-based sensor `sensor.entity_dependency_engine_last_report`. The complete readable report is available in that sensor's `report` attribute, while the sensor state is the report generation timestamp. Reports are always stored privately under:

```text
/config/entity_dependency_engine/reports/
```

### Public report links

Setting `save_public_copy: true` also writes report files below `/config/www/entity_dependency_engine/` and returns `/local/entity_dependency_engine/...` URLs. This is disabled by default because clients that can reach your Home Assistant server may also be able to retrieve files exposed through `/local`. Do not publish reports containing sensitive entity or configuration information unless you understand that trade-off.

## Languages

- English is the source language for code, logs, documentation, and UI strings.
- Swedish UI translations are included.
- Readable reports can be generated in English or Swedish.
- If no report language is supplied, the Home Assistant language is used when supported; otherwise English is used.

## Repository preparation before publishing

Repository metadata is configured for `joakim79a/ha-entity-dependency-engine`. Before the first stable release, verify:

- GitHub repository description and topics are configured
- Issues are enabled
- HACS validation passes
- Hassfest validation passes
- Runtime installation, update, and removal work on a clean Home Assistant instance
- A full GitHub release is created for `v0.1.0`


## Support the project

Entity Dependency Engine is free and open source.

If you find the integration useful, you can support its continued development:

[Buy me a coffee](https://buymeacoffee.com/joakim79a)

Support is entirely optional and does not affect access to features, support, or updates.

## License

MIT
