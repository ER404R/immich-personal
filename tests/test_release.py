from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import release


def published(tag, *, body="", draft=False, prerelease=False, asset_state="uploaded"):
    return {
        "tag_name": tag,
        "draft": draft,
        "prerelease": prerelease,
        "body": body,
        "assets": [{"name": release.APK, "state": asset_state}],
    }


class ReleaseSelectionTest(unittest.TestCase):
    def test_selects_newest_stable_version_numerically(self):
        self.assertEqual(
            release.latest_stable_tag([
                published("v3.4.9"),
                published("v3.4.10"),
                published("v3.5.0-rc.1"),
                published("v3.6.0", prerelease=True),
                published("v3.7.0", draft=True),
            ]),
            "v3.4.10",
        )

    def test_missing_stable_release_fails(self):
        with self.assertRaisesRegex(ValueError, "No published stable release"):
            release.latest_stable_tag([published("v4.0.0", draft=True)])

    def test_resolves_annotated_tag_to_its_commit(self):
        ref = "refs/tags/v3.4.0"
        tag_object = "a" * 40
        commit = "b" * 40
        output = f"{tag_object}\t{ref}\n{commit}\t{ref}^{{}}\n"
        with patch.object(release, "releases", return_value=[published("v3.4.0")]):
            with patch.object(release, "capture", return_value=output):
                self.assertEqual(release.resolve_upstream(), ("v3.4.0", commit))


class PublicationTest(unittest.TestCase):
    def test_keeps_version_codes_increasing_across_migration(self):
        old_releases = [published("3.4.0-rc.0-fork.12.2")]
        self.assertIsNone(release.skip_reason(old_releases, "v3.4.0", "new-inputs", 1301))
        with self.assertRaisesRegex(ValueError, "must exceed 1202"):
            release.skip_reason(old_releases, "v3.4.0", "new-inputs", 1201)

    def test_skips_matching_inputs_and_downgrades(self):
        old_releases = [published("3.4.0-fork.12.1", body="Build inputs: old-inputs")]
        self.assertIn("already shipped", release.skip_reason(old_releases, "v3.4.0", "old-inputs"))
        self.assertIn("older than", release.skip_reason(old_releases, "v3.3.0", "new-inputs"))
        self.assertIsNone(release.skip_reason(old_releases, "v3.4.0", "new-inputs"))

    def test_drafts_and_incomplete_uploads_can_be_retried(self):
        old_releases = [
            published("3.4.0-fork.12.1", body="Build inputs: match", draft=True),
            published("3.4.0-fork.12.2", body="Build inputs: match", asset_state="starter"),
        ]
        self.assertIsNone(release.skip_reason(old_releases, "v3.4.0", "match"))

    def test_can_ship_a_revert_to_older_patch_inputs(self):
        old_releases = [
            published("3.4.0-fork.12.1", body="Build inputs: original"),
            published("3.4.0-fork.13.1", body="Build inputs: modified"),
        ]
        self.assertIsNone(release.skip_reason(old_releases, "v3.4.0", "original", 1401))

    def test_build_fingerprint_includes_upstream_commit(self):
        self.assertNotEqual(
            release.build_inputs("v3.4.0", "a" * 40),
            release.build_inputs("v3.4.0", "b" * 40),
        )

    def test_publishes_assets_to_the_configured_standalone_repository(self):
        recipe_sha = "c" * 40
        args = SimpleNamespace(
            tag="v3.4.0", sha="a" * 40, inputs="inputs", version="3.4.0-fork.10001.1", build_number=1000101,
        )
        with (
            patch.dict(release.os.environ, {"GITHUB_REPOSITORY": "owner/personal", "GITHUB_SHA": recipe_sha}),
            patch.object(release, "capture", return_value=recipe_sha),
            patch.object(release, "releases", return_value=[]),
            patch.object(release.subprocess, "run") as run,
        ):
            release.publish_release(args)

        command = run.call_args.args[0]
        self.assertEqual(command[:6], ["gh", "release", "create", args.version, release.APK, release.SOURCE])
        self.assertEqual(command[command.index("--repo") + 1], "owner/personal")
        self.assertIn(f"Upstream: {release.UPSTREAM} {args.tag} ({args.sha})", command[command.index("--notes") + 1])

    def test_skips_publishing_an_old_workflow_run_after_main_advances(self):
        with (
            patch.dict(release.os.environ, {"GITHUB_REPOSITORY": "owner/personal", "GITHUB_SHA": "c" * 40}),
            patch.object(release, "capture", return_value="d" * 40),
            patch.object(release.subprocess, "run") as run,
        ):
            release.publish_release(SimpleNamespace())

        run.assert_not_called()


class PatchApplicationTest(unittest.TestCase):
    def test_applies_in_order_and_surfaces_conflicts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "upstream"
            source.mkdir()
            scripts = root / "scripts"
            scripts.mkdir()
            apply_patches = scripts / "apply-patches.sh"
            shutil.copyfile(release.ROOT / "scripts/apply-patches.sh", apply_patches)
            patches = root / "patches"
            patches.mkdir()
            self.git(source, "init", "--quiet")
            target = source / "file.txt"
            target.write_text("first\n")
            self.git(source, "add", "file.txt")
            self.write_patch(patches / "02.patch", "second", "third")
            self.write_patch(patches / "01.patch", "first", "second")

            subprocess.run(["bash", str(apply_patches), str(source)], capture_output=True, check=True)
            self.assertEqual(target.read_text(), "third\n")
            self.assertEqual(self.git(source, "show", ":file.txt"), "third\n")

            (patches / "01.patch").unlink()
            self.write_patch(patches / "02.patch", "missing context", "fourth")
            failure = subprocess.run(["bash", str(apply_patches), str(source)], text=True, capture_output=True)
            self.assertNotEqual(failure.returncode, 0)
            self.assertIn("02.patch", failure.stdout)
            self.assertEqual(target.read_text(), "third\n")

    @staticmethod
    def git(source, *arguments):
        return subprocess.check_output(["git", "-C", str(source), *arguments], text=True)

    @staticmethod
    def write_patch(path, previous, current):
        path.write_text(
            "diff --git a/file.txt b/file.txt\n"
            "--- a/file.txt\n"
            "+++ b/file.txt\n"
            "@@ -1 +1 @@\n"
            f"-{previous}\n"
            f"+{current}\n"
        )


if __name__ == "__main__":
    unittest.main()
