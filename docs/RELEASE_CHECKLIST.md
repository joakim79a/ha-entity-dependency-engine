# Release checklist

## Release-candidate validation

- [x] Upgrade from HACS-installed v0.1.0.
- [x] Confirm the existing config entry remains loaded.
- [x] Test the dependency explorer panel.
- [x] Test the existing report workflow.
- [x] Perform a clean HACS installation.
- [x] Confirm HACS, Hassfest, Python, and frontend checks pass.

## Stable release

- [ ] Confirm the stable branch contains version `0.2.0`.
- [ ] Run the full Python test suite.
- [ ] Open a pull request to `main`.
- [ ] Confirm all GitHub Actions checks pass.
- [ ] Merge the stable pull request.
- [ ] Create tag `v0.2.0` from the merge commit.
- [ ] Publish the GitHub release using
      `docs/RELEASE_NOTES_0.2.0.md`.
- [ ] Confirm HACS discovers the stable version.
- [ ] Test the stable update in Home Assistant.
