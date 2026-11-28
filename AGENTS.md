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
- Keep each change focused. Do not add code comments or generate issue text,
  review comments, or discussion answers. Write PR titles and descriptions
  only for this repository when asked to prepare a PR.
- Follow Immich's contribution rules for work intended upstream. Do not open
  upstream PRs with LLM-generated code or use LLMs on upstream issues labeled
  `good first issue`. The upstream sharing, asset ownership, and external
  library features are frozen except for bug fixes. Upstream docs page removals
  and renames require a `docs/static/_redirects` entry.

## Handling issues

- Follow [PATCH_WORKFLOW.md](PATCH_WORKFLOW.md) when asked to handle issues.
  Check this repository's issues and stay within the requested scope.
- Fix each selected issue on its own branch from `main`. Validate and commit
  the fix, then report the branch, commit, and checks.

## Preparing pull requests

- Follow [PATCH_WORKFLOW.md](PATCH_WORKFLOW.md) when asked to prepare PRs.
  Check open PRs for overlapping work.
  Combine the selected issue branches on a fresh branch from `main` when the
  changes belong in one review and release. Keep the issue commits distinct.
- Validate the combined patch series and set the release revision once for
  the batch. If asked to open a PR, push the PR branch and open it against
  `main` in this repository. Link the issues it resolves and leave the merge
  to the maintainer.

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
