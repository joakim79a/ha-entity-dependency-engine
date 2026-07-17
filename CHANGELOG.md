# Changelog

## 0.1.0-dev.2 - 2026-07-17

- Added the native push-updated `sensor.entity_dependency_engine_last_report` entity.
- Exposed the readable report in the sensor's `report` attribute for dashboard use.
- Restored the latest private report from disk when the integration loads.
- Added report counts, summary, file paths, and optional public URLs as sensor attributes.
- Excluded the large `report` attribute from recorder history to avoid unnecessary database growth.
- Added proper config-entry platform forwarding and unloading.

## 0.1.0-dev.1 - 2026-07-16

- Migrated the working prototype into a Home Assistant custom integration structure.
- Added a single-instance config flow.
- Added the `entity_dependency_engine.generate_report` action.
- Added English and Swedish UI translations.
- Added localized English and Swedish readable reports.
- Added private report storage and optional `/local` report copies.
- Preserved and migrated the existing parser and graph test suite.
