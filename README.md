# Immich Personal for Android

This repository builds a personalized Android APK from the newest official stable
[Immich release](https://github.com/immich-app/immich/releases). It installs as
**Immich** with application ID `app.alextran.immich.personal`. Android can
install it alongside official Immich. Each installation has its own login,
permissions, and backup settings.

The patches add a five-hour option to the Android backup delay slider. That
setting delays the background backup triggered by media changes. Foreground
and periodic backups can still upload files sooner.

## Releases

**Fork Android** checks for upstream releases every six hours on the default
branch, and also runs on pushes to `main`. It selects the highest published
stable `vMAJOR.MINOR.PATCH` release, checks out its exact commit, and applies
the numbered patches. Scheduled checks skip the build if the latest published
APK used the same upstream commit and build inputs. Pushes to `main` build the
APK and publish when those inputs differ from the latest published APK.

A successful run publishes the signed ARM64 APK, `immich-er404r.apk`, and the
matching patched source archive. Release tags use `vVERSION-PATCH.REVISION`.
The patch number is the highest numbered file in `patches/`, so upstream
`v3.4.2` with patch `0002` and revision `1` ships as `v3.4.2-2.1`.
Increment `patches/revision` to ship another build for the same upstream version
and patch number, including a fix to an existing patch. Reset it to `1` when
adding a new numbered patch. An upstream version bump uses the current patch
number and revision. The APK version name is the release tag without the
leading `v`.

The release notes record the upstream commit
and link to the build recipe. A failed patch, test, build, or verification leaves
the previous public APK available. The next scheduled run can retry the build.
A manual dispatch on `main` with **Publish a signed APK from main** cleared
runs the checks and compiles Android without releasing an APK.

Set `main` as the default branch and enable Actions on the standalone repository.
Configure these Actions secrets before publishing:

| Secret | Value |
| --- | --- |
| `KEY_JKS` | Base64 of the permanent Android signing keystore |
| `ALIAS` | Alias of the signing key |
| `ANDROID_STORE_PASSWORD` | Keystore password |
| `ANDROID_KEY_PASSWORD` | Signing key password |

If you already distributed `app.alextran.immich.personal`, use its original key.
The standalone version counter starts with a run offset of 10,000. The Android
version code is `(offset + run number) * 100 + run attempt`. If migrating from
an APK with a higher code, set the repository variable `FORK_RUN_OFFSET` before
the first build so the new code exceeds it. Keep the signing key and version
counter continuous for later updates.

In Obtainium, add the URL of this standalone repository as a GitHub source.
If you added the old `-fork\.` release filter, clear it so Obtainium can see
the new tags. If needed, use the APK filename filter `^immich-er404r\.apk$`.
If you previously installed a build under
`app.alextran.immich.er404r`, install the `.personal` build separately and sign
in again. For an existing `.personal` install, point Obtainium at this
repository to receive future updates.

## Working on patches

Install Git, the GitHub CLI, Python 3, and mise. Authenticate the GitHub CLI for
the release lookup, then run:

```sh
mise //:prepare
mise //:test
mise //:lint
```

`prepare` fetches the latest stable release into the ignored `.immich/` checkout.
To reproduce a release, pass its upstream SHA to `mise //:prepare` after checking
out the build recipe linked in its release notes. Move any existing `.immich/`
checkout before preparing another one.

Each patch is applied to both the index and worktree. For a new change,
edit the prepared source and run its mise tasks from `.immich/`. Mark new files
for inclusion with `git -C .immich add -N -- path/to/file`, then export the
changes with `git -C .immich diff --binary --full-index`. Save that diff as the
next numbered patch and prepare a fresh checkout to validate the series.

The Android release tasks live in this repository's `mobile/mise.toml`. Run
`mise //mobile:build:fork-apk` and `mise //mobile:verify:fork-apk` from the recipe
root. The tasks use Immich's pinned tools from the prepared checkout. The
recipe's `AGENTS.md` stays in the recipe root.

Keep any signing backups in the ignored `.fork-private/` directory and back
them up separately.

## Pull requests and branch protection

Pull requests run recipe tests, Dart analysis and formatting, Flutter and Rust
tests, and Android compilation. PR builds use no release signing credentials.
A push to `main` triggers the signed Android build. It publishes when the
upstream source or build inputs differ from the latest published APK. The
scheduled upstream release check continues to run independently.

Anyone with repository write access can push to `main` directly. The active
ruleset in `.github/main-ruleset.json` blocks force-pushes and deletion.
