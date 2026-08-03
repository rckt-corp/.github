# .github

Default community health files and org profile for [rckt corp.](https://github.com/rckt-corp).

## Contents

- [`profile/README.md`](profile/README.md) — org profile shown on the rckt-corp GitHub page
- [`.github/workflows/enforce-runners.yml`](.github/workflows/enforce-runners.yml) — org-required check that jobs use rckt self-hosted runners only
- [`.github/actions/enforce-runners`](.github/actions/enforce-runners) — composite action implementing the allowlist
- `.github/SECURITY.md` _(planned)_ — security policy and vulnerability reporting
- `.github/CONTRIBUTING.md` _(planned)_ — contribution guidelines for all repos

Files placed here apply as defaults to all rckt-corp repositories that don't define their own.

## Allowed runners

Workflow jobs must target one of:

| `runs-on` | Purpose |
|-----------|---------|
| `rckt-arc-lite` | Default CI (lint, tests, tofu, light jobs) |
| `rckt-arc` | Docker / heavier jobs |
| labels including `native-macos` | Native macOS fleet |

GitHub-hosted labels (`ubuntu-*`, `windows-*`, `macos-*`) are rejected.

Enforcement:

1. Organization ruleset **require-allowed-runners** requires this workflow on PRs to `main`/`master`.
2. Org setting **Standard hosted runners → Disable for all repositories** (UI) so disallowed jobs cannot schedule.
