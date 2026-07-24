# Release checklist

## Repository

- [ ] Work from `release/0.2.0` based on the tested alpha.7 commit.
- [ ] Add the three release screenshots.
- [ ] Review all English documentation.
- [ ] Run all tests and JavaScript syntax checks.
- [ ] Push the release branch and open a pull request to `main`.
- [ ] Confirm HACS, Hassfest, Python, and frontend checks pass.

## Prerelease

- [ ] Merge to `main`.
- [ ] Create tag `v0.2.0-rc.1` from the merge commit.
- [ ] Create a full GitHub release and mark it as a prerelease.
- [ ] Use `docs/RELEASE_NOTES_0.2.0-rc.1.md` as the release description.
- [ ] Confirm HACS discovers and installs it.

## Runtime validation

- [ ] Upgrade from HACS-installed v0.1.0.
- [ ] Confirm the config entry remains loaded.
- [ ] Test the panel and existing report workflow.
- [ ] Perform a clean HACS installation.
- [ ] Test rollback to v0.1.0.

## Stable release

- [ ] Fix release-blocking defects only.
- [ ] Change rc.1 to stable 0.2.0.
- [ ] Repeat validation.
- [ ] Create the full GitHub release `v0.2.0`.
