# v0.1.0 Compatibility Contract

This document defines the public behaviour introduced in Entity Dependency
Engine v0.1.0.

Development of the visual dependency panel must remain additive. Existing
v0.1.0 functionality must not be removed, renamed, or silently changed.

## Protected Home Assistant action

The following action must remain available:

```text
entity_dependency_engine.generate_report
```

### Protected input fields

- `entity_id`
- `language`
- `include_structural`
- `max_depth`
- `save_public_copy`

Default behaviour must remain:

- `include_structural: false`
- `save_public_copy: false`
- English fallback when the selected Home Assistant language is unsupported

Supported report languages must continue to include:

- `en`
- `sv`

### Protected response fields

The action response must continue to provide:

- `ok`
- `entity_id`
- `summary`
- `parents`
- `children`
- `ancestors`
- `descendants`
- `broken`
- `build_warnings`
- `generated`
- `private_file`
- `private_debug_file`
- `private_latest_file`

When report text is requested, the response must continue to provide:

- `report`

When public report copies are enabled, the response must continue to provide:

- `url`
- `debug_url`
- `latest_url`

Additional response fields may be added in future releases, but the protected
fields must not be removed or assigned incompatible meanings.

## Protected sensor

The integration must continue to create the last-report sensor with the stable
suggested entity ID:

```text
sensor.entity_dependency_engine_last_report
```

Its unique ID must remain:

```text
last_report
```

The sensor state must continue to represent the report generation timestamp.

The following sensor attributes must remain supported:

- `report`
- `entity_id`
- `summary`
- `parents`
- `children`
- `ancestors`
- `descendants`
- `broken`
- `build_warnings`
- `private_file`
- `private_debug_file`
- `url`
- `debug_url`

The large `report` attribute must remain excluded from recorder history unless
a later implementation provides an equally safe replacement.

## Protected report storage

Private reports must continue to be stored below:

```text
/config/entity_dependency_engine/reports/
```

The latest readable report must continue to be written as:

```text
latest_report.txt
```

Entity-specific report filenames must remain compatible with the v0.1.0
format unless a transparent migration or compatibility layer is provided.

When public copies are explicitly enabled, reports must continue to be written
below:

```text
/config/www/entity_dependency_engine/
```

and exposed through:

```text
/local/entity_dependency_engine/
```

Public copies must remain disabled by default.

## Protected setup behaviour

The integration must continue to:

- install through HACS
- support setup through the Home Assistant config flow
- unload cleanly
- restore the latest private report after Home Assistant restarts
- operate without requiring YAML configuration

## Panel development rules

The visual panel is an additional interface and must not replace the existing
action, sensor, text reports, debug reports, scripts, or dashboard workflow.

The panel must use a separate graph-data API.

New panel code must not require users of v0.1.0 functionality to:

- recreate the integration
- rename the existing sensor
- rewrite existing scripts
- rewrite existing dashboard cards
- move existing report files
- enable public report storage

## Required regression checks

Before any panel release is merged into `main`, the following must pass:

1. Existing unit tests.
2. HACS validation.
3. Hassfest validation.
4. Report generation in English.
5. Report generation in Swedish.
6. Private report generation.
7. Optional public report generation.
8. Last-report sensor update.
9. Last-report restoration after restart.
10. Existing v0.1.0 script example.
11. Existing v0.1.0 dashboard example.
12. Upgrade from the latest stable v0.1.x release.

## Change policy

Compatible additions are allowed.

Breaking changes require:

- an explicit migration path
- documentation
- regression coverage
- a major-version decision when the public stable contract is affected

The published v0.1.0 tag remains immutable.
