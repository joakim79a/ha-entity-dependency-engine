# Upgrading

## v0.1.0 to v0.2.0

1. Create and download a full Home Assistant backup.
2. Confirm v0.1.0 currently generates a report successfully.
3. Record the state and attributes of `sensor.entity_dependency_engine_last_report`.
4. Enable prereleases for the repository in HACS.
5. Install `v0.2.0` and restart Home Assistant.
6. Confirm the existing config entry remains loaded.
7. Test panel search, graph loading, expansion, history, direct links, centering, and reset.
8. Run the existing report script or action.
9. Confirm the latest-report sensor and existing dashboard still work.

## Clean-install test

Use a disposable test instance or a system with a verified backup. Remove the config entry and HACS package, restart, install v0.2.0, restart, add the integration, and test both panel and report generation.

## Rollback

Reinstall v0.1.0 through HACS and restart Home Assistant. The release candidate does not intentionally migrate or rewrite config entries, report files, scripts, automations, or dashboards.
