# Migration status

## Completed in this package

- Clean `custom_components/entity_dependency_engine` layout
- Pure analysis engine vendored inside the integration
- Internal imports converted to package-relative imports
- Home Assistant config flow
- Native Home Assistant action with response data
- Native push-updated latest-report sensor for dashboard use
- English source UI and Swedish translation
- English and Swedish human-readable reports
- Private report directory and opt-in public copies
- HACS manifest, README, license, changelog, and validation workflows
- Original parser/graph tests migrated

## Required before public release

1. Confirm or change the MIT license choice.
2. Review or replace the provisional brand icon.
3. Test on a clean Home Assistant installation.
4. Run Hassfest and HACS validation on GitHub.
5. Decide whether direct reads from `.storage` remain acceptable for v0.1.0 or should be replaced by Home Assistant registry APIs.
6. Publish a full GitHub release named `v0.1.0`.

Runtime installation and report generation have been verified on the current Home Assistant system.

## Deliberate scope boundary

No new parsers or analysis features are added during packaging. New analysis work belongs in the backlog until installation, upgrade, and removal are reliable.
