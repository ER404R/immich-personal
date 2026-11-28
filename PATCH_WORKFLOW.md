# Patch workflow

## Handling issues

1. Check the requested issues in `ER404R/immich-personal`. If the request
   names an area, check issues in that area. Reuse existing issue branches
   when they already address the requested work.
2. Fetch the latest `main` and create a separate branch for each selected
   issue, such as `issue/42-backup-delay`. Use separate worktrees if several
   issues are in progress so each has its own prepared `.immich/` checkout.
3. Follow the patch steps below for changes to Immich itself. Make recipe
   changes directly in this repository. Run the checks relevant to the fix
   and commit the issue's changes on its branch. Keep `patches/revision`
   unchanged.
4. Report the issue number, branch name, commit SHA, and checks or blockers.
   Leave the branch local unless asked to make it available on GitHub.

## Editing Immich patches

From the recipe root, run `mise //:prepare` to check out the latest official
stable release and apply the numbered patches. To reproduce a particular
release, check out the recipe commit linked in its release notes and pass
the full upstream SHA from those notes to `mise //:prepare`. Record the
prepared upstream SHA with `git -C .immich rev-parse HEAD` so you can validate
against the same base later. Move any existing `.immich/` checkout aside
before preparing a fresh one.

Read the applicable upstream `AGENTS.md` before editing the prepared source.
Run upstream mise tasks from `.immich/` and use upstream generators for
generated files. Add translations only to `i18n/en.json` and use the upstream
formatting and generation tasks.

- **Add a feature patch.** Edit the prepared source. For new files, mark them
  with `git -C .immich add -N -- path/to/file`. Export the diff with
  `git -C .immich diff --binary --full-index` and save it under the next
  numbered name, such as `patches/0003-feature.patch`. Leave the edits
  unstaged in `.immich/` so the diff compares them with the index, which
  already contains the existing patches.
- **Fix an existing patch.** In a fresh prepared checkout, reverse later
  patches in descending order, then reverse the target patch, using
  `git -C .immich apply --reverse --index` with the patch paths relative
  to `.immich/`. Reapply the target patch with `git -C .immich apply`
  without `--index`. This leaves the earlier patches in the index and
  the target patch in the worktree. Make the fix, mark new files with
  `git -C .immich add -N`, and replace the target patch with the exported
  diff. Update any later patches that depend on the change if needed.
- **Verify the exported patches.** Move the edited checkout aside and run
  `mise //:prepare <upstream-sha>` from the recipe root. This reapplies the
  full series in filename order. Run relevant Immich checks from the fresh
  checkout and keep both prepared checkouts out of the recipe commit.

## Preparing pull requests

1. Check open PRs for overlap with the requested issue branches. If separate
   PRs already exist, check which commits are still needed. For fixes that
   belong together, make a fresh PR branch from the latest `main` and
   cherry-pick the selected commits in dependency order. Keep unrelated
   changes with different review or release needs in their own PRs.
2. Resolve conflicts as you cherry-pick. Give new patches distinct, sequential
   numbers and preserve their dependencies. For overlapping patch edits,
   regenerate the affected patch against the preceding patches whenever
   needed. Check the final diff for duplicate patch numbers and unintended
   changes.
3. Check the latest published fork tag and set `patches/revision` once for
   the batch. Set it to `1` when the highest patch number increases.
   Increment it for changed build inputs when the highest patch number
   stays the same. The scheduled workflow uses the current patch number and
   revision when upstream publishes a newer version. Keep the revision
   unchanged for docs-only changes. Recheck numbering if another batch
   lands on `main` before this one.
4. From the recipe root, run `mise //:prepare` against the latest stable
   upstream on a fresh checkout for patch changes. Run `mise //:test` and
   `mise //:lint`, plus the relevant upstream mise tasks from `.immich/`.
   The **Fork Android** workflow runs the full Android checks on PRs.
5. If asked to open a PR, push the PR branch and open it against `main` in
   `ER404R/immich-personal`. Summarize the changes, list the checks, and
   link each issue fully resolved by the PR with its own closing keyword.
   Reference any PRs it supersedes. Report the PR link and leave the merge
   to the maintainer.
