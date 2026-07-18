# Entity Dependency Engine

Entity Dependency Engine is a read-only Home Assistant custom integration
that builds a directed dependency graph for a selected entity.

It can trace direct and recursive upstream and downstream relationships
before you rename, disable, replace, or remove an entity.

> Project status: version 0.1.0 is the first public release. Installation
> through HACS, integration removal and re-creation, report generation,
> sensor updates, and dashboard output have been tested on the maintainer's
> Home Assistant installation.

## Current capabilities

The engine currently analyses:

- Home Assistant entity, device, and config-entry registries
- GUI-created template entities
- Utility Meter helpers
- Derivative helpers
- Min/Max helpers
- History Stats helpers
- Integration helpers
- Threshold helpers
- Groups
- Switch-as-X helpers
- Automations and scripts
- Direct parents and children
- Recursive ancestors and descendants
- Broken or unresolved entity references
- Structural relations to devices and config entries

## Installation with HACS

Entity Dependency Engine is currently installed as a custom HACS repository.

1. Open HACS in Home Assistant.
2. Open the menu in the upper-right corner.
3. Select **Custom repositories**.
4. Add:

   ```text
   https://github.com/joakim79a/ha-entity-dependency-engine
   ```

5. Select **Integration** as the repository type.
6. Search for **Entity Dependency Engine** in HACS.
7. Download the integration.
8. Restart Home Assistant.
9. Open **Settings > Devices & services > Add integration**.
10. Search for **Entity Dependency Engine** and add it.

## Manual installation

1. Copy:

   ```text
   custom_components/entity_dependency_engine
   ```

   to:

   ```text
   /config/custom_components/entity_dependency_engine
   ```

2. Restart Home Assistant.
3. Open **Settings > Devices & services > Add integration**.
4. Search for **Entity Dependency Engine** and add it.

## Generate a report

Call the Home Assistant action:

```yaml
action: entity_dependency_engine.generate_report
data:
  entity_id: sensor.example
  language: en
  include_structural: false
  save_public_copy: false
response_variable: dependency_report
```

Available options:

| Option | Description |
|---|---|
| `entity_id` | Entity to analyse |
| `language` | Report language: `en` or `sv` |
| `include_structural` | Include device and config-entry relations |
| `save_public_copy` | Also save report files below `/config/www` |
| `max_depth` | Optional maximum recursive graph depth |

The action returns counts, a summary, file paths, and the readable report
when a response is requested.

It also updates:

```text
sensor.entity_dependency_engine_last_report
```

The sensor state is the report generation timestamp. The complete readable
report is available in the sensor's `report` attribute.

## Private report storage

Reports are always stored privately under:

```text
/config/entity_dependency_engine/reports/
```

## Public report links

Setting:

```yaml
save_public_copy: true
```

also writes report files below:

```text
/config/www/entity_dependency_engine/
```

and returns URLs below:

```text
/local/entity_dependency_engine/
```

This is disabled by default. Clients that can reach your Home Assistant
server may also be able to retrieve files exposed through `/local`.

Dependency reports may contain sensitive entity names and configuration
information. Only enable public copies when you understand that trade-off.

## script example (sv)
```yaml
alias: "System: Analysera entitetsrelationer"
description: Bygger beroendegrafen för en vald entitet och sparar rapporten.
icon: mdi:file-tree
mode: single
fields:
  target_entity:
    name: Entitet
    description: Välj den entitet vars relationer ska analyseras.
    required: true
    selector:
      entity: {}
sequence:
  - action: entity_dependency_engine.generate_report
    data:
      entity_id: "{{ target_entity }}"
      language: sv
      include_structural: false
      save_public_copy: true
    response_variable: dependency_result
  - action: persistent_notification.create
    data:
      notification_id: entity_dependency_report
      title: "Entitetsrapport: {{ target_entity }}"
      message: >-
        {{ dependency_result.summary }}

        Föräldrar: {{ dependency_result.parents }} Barn: {{
        dependency_result.children }} Förfäder: {{ dependency_result.ancestors
        }} Ättlingar: {{ dependency_result.descendants }}

        Brutna referenser: {{ dependency_result.broken }} Build-varningar: {{
        dependency_result.build_warnings }}

        [Öppna rapporten]({{ dependency_result.url }})

        [Öppna debugrapporten]({{ dependency_result.debug_url }})

        Skapad: {{ dependency_result.generated }}
  ```

## Dashboard example (sv)

```yaml
type: vertical-stack
cards:
  - type: button
    entity: script.system_analysera_entitetsrelationer
    name: Analysera entitet
    icon: mdi:file-tree
    show_state: false
    tap_action:
      action: more-info
    hold_action:
      action: more-info
  - type: markdown
    title: Senaste entitetsrapport
    content: |-
      {% set report = state_attr(
        'sensor.entity_dependency_engine_last_report',
        'report'
      ) %}

      {% if report %}
      ```text
      {{ report }}
      ```
      {% else %}
      Ingen rapport har skapats ännu.

      Tryck på **Analysera entitet** ovan.
      {% endif %}

  ```

## Languages

- English is the source language for code, logs, documentation, and UI text.
- Swedish UI translations are included.
- Readable reports can be generated in English or Swedish.
- When no report language is supplied, the Home Assistant language is used
  when supported. Otherwise English is used.

## Reporting issues

Open an issue in the GitHub repository and include:

- Home Assistant version
- Entity Dependency Engine version
- The entity type being analysed
- Relevant Home Assistant log messages
- A description of the expected and actual result

Avoid publishing reports containing private entity names, device names,
addresses, tokens, or other sensitive configuration information.

## Support the project

Entity Dependency Engine is free and open source.

If you find the integration useful, you can support its continued
development:

[Buy me a coffee](https://buymeacoffee.com/joakim79a)

Support is entirely optional and does not affect access to features,
support, or updates.

## License

MIT
