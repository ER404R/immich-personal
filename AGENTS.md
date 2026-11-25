# AGENTS.md

This repository builds a standalone Android distribution from official stable
Immich releases. The source tree is prepared in the ignored `.immich/` directory.
The patches, build scripts, and workflow define the distribution.

## Development

- Run build, lint, test, and code generation tasks through mise. The recipe's
  tasks are `mise //:prepare`, `mise //:test`, and `mise //:lint`. Run Immich
  tasks from the prepared source tree.
- Read the applicable directory's `AGENTS.md` in the prepared source before
  changing code in `server/`, `web/`, `mobile/`, `native/`, `machine-learning/`
  or `e2e/`. Keep changes in ordered patches by feature.
- Use upstream code generation for the OpenAPI clients, generated SQL, generated
  Dart, and bindings. Add translations only to `i18n/en.json` and format and
  regenerate them with the upstream mise tasks.
- Keep each change focused. Do not add code comments or generate PR titles,
  descriptions, issue text, review comments, or discussion answers.
- Follow Immich's contribution rules for work intended upstream. Do not open
  upstream PRs with LLM-generated code or use LLMs on upstream issues labeled
  `good first issue`. The upstream sharing, asset ownership, and external
  library features are frozen except for bug fixes. Upstream docs page removals
  and renames require a `docs/static/_redirects` entry.

## Android releases

- Preserve application ID `app.alextran.immich.personal`, launcher name
  `Immich`, Kotlin namespace `app.alextran.immich`, and release asset filename
  `immich-er404r.apk`.
- Build signed ARM64 release APKs with the permanent keystore and verify the
  package, launcher name, signer, and ABI with `mise //mobile:verify:fork-apk`.
  Keep signing backups private in `.fork-private/`. Preserve the increasing
  Android version counter and upstream version prefix.
- Keep the five-hour backup option stored as 18,000 seconds, including when
  converting legacy millisecond settings. It delays the media-change backup
  trigger. Foreground and periodic backups can still upload sooner.
- Release only from `main`. The scheduled workflow checks official stable
  releases and leaves the previous release available when a build fails.
