# Contributing

## Bug reports

Include Home Assistant version, integration version, installation method, affected entity type, reproduction steps, expected behaviour, actual behaviour, and relevant logs.

Remove private names, addresses, tokens, precise locations, and sensitive configuration.

## Feature requests

Describe the problem, expected workflow, affected area, and compatibility impact.

## Development

Use a feature branch, preserve the v0.1 compatibility contract, add regression tests, and write code and documentation in English.

```bash
python -m pytest
cp custom_components/entity_dependency_engine/frontend/entity-dependency-layout.js /tmp/layout.mjs
cp custom_components/entity_dependency_engine/frontend/entity-dependency-panel.js /tmp/panel.mjs
node --check /tmp/layout.mjs
node --check /tmp/panel.mjs
```
