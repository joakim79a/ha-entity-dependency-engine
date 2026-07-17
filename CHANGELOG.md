# Changelog

## 0.1.0 - 2026-07-17

First public release.

- Added installation through HACS as a custom repository.
- Added a single-instance Home Assistant config flow.
- Added the `entity_dependency_engine.generate_report` action.
- Added the native push-updated
  `sensor.entity_dependency_engine_last_report` entity.
- Added recursive dependency analysis for parents, children, ancestors,
  and descendants.
- Added support for entity, device, and config-entry registries.
- Added parsers for GUI templates, Utility Meter, Derivative, Min/Max,
  History Stats, Integration, Threshold, Group, and Switch-as-X helpers.
- Added automation and script reference analysis.
- Added broken and unresolved reference reporting.
- Added English and Swedish UI translations.
- Added readable reports in English and Swedish.
- Added private report storage.
- Added optional public report copies through `/local`.
- Added restoration of the latest private report after Home Assistant restarts.
- Added HACS, Hassfest, and unit-test validation through GitHub Actions.
- Added project funding through Buy Me a Coffee.

## 0.1.0-dev.2 - 2026-07-17

- Added the native push-updated
  `sensor.entity_dependency_engine_last_report` entity.
- Exposed the readable report in the sensor's `report` attribute.
- Restored the latest private report from disk when the integration loads.
- Added report counts, summary, file paths, and optional public URLs as
  sensor attributes.
- Excluded the large `report` attribute from recorder history.
- Added proper config-entry platform forwarding and unloading.

## 0.1.0-dev.1 - 2026-07-16

- Migrated the working prototype into a Home Assistant custom integration.
- Added a single-instance config flow.
- Added the `entity_dependency_engine.generate_report` action.
- Added English and Swedish UI translations.
- Added localized English and Swedish readable reports.
- Added private report storage and optional `/local` report copies.
- Preserved and migrated the existing parser and graph test suite.