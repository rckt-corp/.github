# .github

Default community health files and org profile for [rckt corp.](https://github.com/rckt-corp).

## Contents

- [`profile/README.md`](profile/README.md) — org profile shown on the rckt-corp GitHub page
- `.github/SECURITY.md` _(planned)_ — security policy and vulnerability reporting
- `.github/CONTRIBUTING.md` _(planned)_ — contribution guidelines for all repos

Files placed here apply as defaults to all rckt-corp repositories that don't define their own.

## Runner policy

Org-required runner allowlisting lives in [`rckt-corp/terraform-infrastructure`](https://github.com/rckt-corp/terraform-infrastructure):

- `.github/workflows/enforce-runners.yml`
- `.github/actions/enforce-runners`

Wired via the organization ruleset **require-allowed-runners**.
