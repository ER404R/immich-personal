import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


UPSTREAM = "immich-app/immich"
UPSTREAM_URL = f"https://github.com/{UPSTREAM}.git"
APK = "immich-er404r.apk"
SOURCE = "immich-personal-source.tar.gz"
STABLE_TAG = re.compile(r"v([0-9]+)\.([0-9]+)\.([0-9]+)")
FORK_TAG = re.compile(r"v([0-9]+)\.([0-9]+)\.([0-9]+)-([1-9][0-9]*)\.([1-9][0-9]*)")
LEGACY_TAG = re.compile(r"v?([0-9]+)\.([0-9]+)\.([0-9]+)(?:-[0-9A-Za-z.]+)?-fork\.([0-9]+)\.([0-9]+)")
PATCH_REVISION = Path("patches/revision")
ROOT = Path(__file__).resolve().parent.parent


def capture(*command):
    return subprocess.check_output(command, text=True)


def releases(repository):
    pages = json.loads(capture("gh", "api", "--paginate", "--slurp", f"repos/{repository}/releases?per_page=100"))
    return [release for page in pages for release in page]


def stable_version(tag):
    return tuple(map(int, STABLE_TAG.fullmatch(tag).groups()))


def latest_stable_tag(all_releases):
    tags = [
        release["tag_name"]
        for release in all_releases
        if not release["draft"] and not release["prerelease"] and STABLE_TAG.fullmatch(release["tag_name"])
    ]
    if not tags:
        raise ValueError(f"No published stable release found for {UPSTREAM}")
    return max(tags, key=stable_version)


def resolve_upstream():
    tag = latest_stable_tag(releases(UPSTREAM))
    ref = f"refs/tags/{tag}"
    lines = capture("git", "ls-remote", "--exit-code", UPSTREAM_URL, ref, f"{ref}^{{}}").splitlines()
    refs = {name: commit for commit, name in (line.split() for line in lines)}
    sha = refs.get(f"{ref}^{{}}") or refs[ref]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError(f"Unexpected upstream commit SHA for {tag}")
    return tag, sha


def build_inputs(tag, sha):
    digest = hashlib.sha256(f"{tag}\n{sha}\n".encode())
    paths = [
        *ROOT.glob("patches/*.patch"),
        ROOT / PATCH_REVISION,
        *ROOT.glob("scripts/*.sh"),
        ROOT / "scripts/release.py",
        ROOT / "mise.toml",
        ROOT / "mobile/mise.toml",
        ROOT / ".github/workflows/fork-android.yml",
    ]
    for path in sorted(paths):
        digest.update(f"{path.relative_to(ROOT)}\0".encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def fork_version(upstream_tag):
    patch_number = max(int(path.name.split("-", 1)[0]) for path in (ROOT / "patches").glob("*.patch"))
    revision = (ROOT / PATCH_REVISION).read_text().strip()
    version = f"{upstream_tag}-{patch_number}.{revision}"
    if not FORK_TAG.fullmatch(version):
        raise ValueError(f"Invalid release tag {version}; set {PATCH_REVISION} to a positive integer without leading zeros")
    return version


def published_forks(all_releases):
    for release in all_releases:
        tag = release["tag_name"]
        legacy = LEGACY_TAG.fullmatch(tag)
        version = FORK_TAG.fullmatch(tag) or legacy
        if release["draft"] or release["prerelease"] or not version:
            continue
        if not any(asset["name"] == APK and asset["state"] == "uploaded" for asset in release["assets"]):
            continue
        numbers = tuple(map(int, version.groups()))
        if legacy:
            yield release, (*numbers[:3], 0, 0), numbers[3] * 100 + numbers[4]
        else:
            code = re.search(r"^Android version code: ([0-9]+)$", release["body"] or "", re.MULTILINE)
            if not code:
                raise ValueError(f"Missing Android version code in release notes for {tag}")
            yield release, numbers, int(code[1])


def skip_reason(all_releases, version, inputs, build_number=None):
    forks = list(published_forks(all_releases))
    if not forks:
        return None

    newest_release, newest_version, _ = max(forks, key=lambda entry: entry[1])
    requested_version = tuple(map(int, FORK_TAG.fullmatch(version).groups()))
    if requested_version[:3] < newest_version[:3]:
        return f"{version} is older than published release {newest_release['tag_name']}"

    latest_release, _, published_number = max(forks, key=lambda entry: entry[2])
    if f"Build inputs: {inputs}" in (latest_release["body"] or "").splitlines():
        return f"These build inputs already shipped in {latest_release['tag_name']}"

    if requested_version <= newest_version:
        raise ValueError(
            f"Release tag {version} must follow {newest_release['tag_name']}; "
            f"increase the patch number or update {PATCH_REVISION}"
        )
    if build_number is not None and build_number <= published_number:
        raise ValueError(f"Android version code {build_number} must exceed {published_number}")
    return None


def plan(publish):
    tag, sha = resolve_upstream()
    version = fork_version(tag)
    inputs = build_inputs(tag, sha)
    reason = skip_reason(releases(os.environ["GITHUB_REPOSITORY"]), version, inputs) if publish else None
    print(reason or f"Preparing {version} from {UPSTREAM} {tag} ({sha})", flush=True)
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        print(f"tag={tag}\nsha={sha}\nversion={version}\ninputs={inputs}\nbuild={str(reason is None).lower()}", file=output)


def publish_release(args):
    repository = os.environ["GITHUB_REPOSITORY"]
    recipe_sha = os.environ["GITHUB_SHA"]
    main_sha = capture("gh", "api", f"repos/{repository}/git/ref/heads/main", "--jq", ".object.sha").strip()
    if main_sha != recipe_sha:
        print(f"Skipping publication because main advanced to {main_sha}")
        return

    reason = skip_reason(releases(repository), args.version, args.inputs, args.build_number)
    if reason:
        print(reason)
        return

    notes = (
        f"Upstream: {UPSTREAM} {args.tag} ({args.sha})\n"
        f"Build inputs: {args.inputs}\n"
        f"Android version code: {args.build_number}\n\n"
        f"Build recipe: https://github.com/{repository}/tree/{recipe_sha}\n"
        f"The attached {SOURCE} contains the patched Immich source."
    )
    subprocess.run(
        [
            "gh", "release", "create", args.version, APK, SOURCE,
            "--repo", repository, "--target", recipe_sha,
            "--title", args.version, "--notes", notes, "--latest",
        ],
        check=True,
    )


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("resolve")
    plan_parser = commands.add_parser("plan")
    plan_parser.add_argument("--publish", choices=("true", "false"), required=True)
    publish_parser = commands.add_parser("publish")
    publish_parser.add_argument("tag")
    publish_parser.add_argument("sha")
    publish_parser.add_argument("inputs")
    publish_parser.add_argument("version")
    publish_parser.add_argument("build_number", type=int)
    args = parser.parse_args()

    if args.command == "resolve":
        print(resolve_upstream()[1])
    elif args.command == "plan":
        plan(args.publish == "true")
    else:
        publish_release(args)


if __name__ == "__main__":
    main()
