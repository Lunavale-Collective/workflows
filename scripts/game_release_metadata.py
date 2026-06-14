#!/usr/bin/env python3
"""Generate Lunavale game release metadata and enforce release version ordering."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


BASE62_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
HEX_SHA256_RE = re.compile(r"\b[a-fA-F0-9]{64}\b")
VERSION_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\."
    r"(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<pre>[0-9A-Za-z.-]+))?"
    r"(?:\+[0-9A-Za-z.-]+)?$"
)
VERSION_BUILD_RE = re.compile(r"^(?P<version>.+?)\s+build\s+(?P<suffix>[0-9A-Za-z]{6})$")
TAG_BUILD_RE = re.compile(r"^(?P<version>.+)-(?P<suffix>[0-9A-Za-z]{6})$")


@dataclass(frozen=True)
class Version:
    raw: str
    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...]

    @classmethod
    def parse(cls, value: str) -> "Version":
        raw = value.strip()
        if raw.startswith("v"):
            raw = raw[1:]
        match = VERSION_RE.match(raw)
        if not match:
            raise ValueError(f"Version '{value}' is not supported semantic version syntax.")
        prerelease = tuple((match.group("pre") or "").split(".")) if match.group("pre") else ()
        return cls(
            raw=raw,
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            prerelease=prerelease,
        )

    @property
    def is_prerelease(self) -> bool:
        return bool(self.prerelease)

    def compare(self, other: "Version") -> int:
        left = (self.major, self.minor, self.patch)
        right = (other.major, other.minor, other.patch)
        if left != right:
            return -1 if left < right else 1
        return compare_prerelease(self.prerelease, other.prerelease)


@dataclass(frozen=True)
class GameRelease:
    version: Version
    tag_name: str
    name: str
    hash_suffix: str | None
    repo_files_sha256: str | None


def compare_prerelease(left: tuple[str, ...], right: tuple[str, ...]) -> int:
    if not left and not right:
        return 0
    if not left:
        return 1
    if not right:
        return -1
    for left_part, right_part in zip(left, right):
        if left_part == right_part:
            continue
        left_numeric = left_part.isdigit()
        right_numeric = right_part.isdigit()
        if left_numeric and right_numeric:
            left_int = int(left_part)
            right_int = int(right_part)
            return -1 if left_int < right_int else 1
        if left_numeric:
            return -1
        if right_numeric:
            return 1
        return -1 if left_part < right_part else 1
    if len(left) == len(right):
        return 0
    return -1 if len(left) < len(right) else 1


def run_git(repo_root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def read_bundle_version(project_root: Path) -> str:
    settings = project_root / "ProjectSettings" / "ProjectSettings.asset"
    match = re.search(r"^\s*bundleVersion:\s*(\S+)\s*$", settings.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        raise RuntimeError(f"Could not find bundleVersion in {settings}.")
    return match.group(1)


def read_editor_version(project_root: Path) -> str:
    version_file = project_root / "ProjectSettings" / "ProjectVersion.txt"
    match = re.search(r"^m_EditorVersion:\s*(\S+)\s*$", version_file.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        raise RuntimeError(f"Could not find m_EditorVersion in {version_file}.")
    return match.group(1)


def repo_files_hash(repo_root: Path) -> str:
    paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=repo_root)
    digest = hashlib.sha256()
    for raw_path in paths.split(b"\0"):
        if not raw_path:
            continue
        path = raw_path.decode("utf-8")
        file_path = repo_root / path
        if not file_path.is_file():
            continue
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(file_path.read_bytes()).hexdigest().encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def base62_suffix(hex_sha256: str, length: int = 6) -> str:
    value = int(hex_sha256, 16)
    encoded = ""
    while value:
        value, remainder = divmod(value, len(BASE62_ALPHABET))
        encoded = BASE62_ALPHABET[remainder] + encoded
    encoded = encoded or "0"
    return encoded[-length:].rjust(length, "0")


def fetch_releases(release_repo: str, token: str) -> list[GameRelease]:
    url = f"https://api.github.com/repos/{release_repo}/releases?per_page=100"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "lunavale-game-release-metadata",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    releases: list[GameRelease] = []
    for release in payload:
        parsed = parse_release(release)
        if parsed is None:
            print(
                f"warning: ignoring non-semver game-builds release "
                f"'{release.get('tag_name') or release.get('name')}'",
                file=sys.stderr,
            )
            continue
        releases.append(parsed)
    return releases


def parse_release(release: dict[str, object]) -> GameRelease | None:
    tag_name = str(release.get("tag_name") or "")
    name = str(release.get("name") or "")
    body = str(release.get("body") or "")
    hash_suffix: str | None = None

    for candidate in (name, tag_name):
        match = VERSION_BUILD_RE.match(candidate) or TAG_BUILD_RE.match(candidate)
        if not match:
            continue
        try:
            version = Version.parse(match.group("version"))
        except ValueError:
            continue
        hash_suffix = match.group("suffix")
        return GameRelease(
            version=version,
            tag_name=tag_name,
            name=name,
            hash_suffix=hash_suffix,
            repo_files_sha256=extract_repo_files_sha256(release, body),
        )

    for candidate in (tag_name, name):
        if not candidate:
            continue
        try:
            version = Version.parse(candidate)
        except ValueError:
            continue
        return GameRelease(
            version=version,
            tag_name=tag_name,
            name=name,
            hash_suffix=hash_suffix,
            repo_files_sha256=extract_repo_files_sha256(release, body),
        )

    return None


def extract_repo_files_sha256(release: dict[str, object], body: str) -> str | None:
    body_match = HEX_SHA256_RE.search(body)
    if body_match:
        return body_match.group(0).lower()

    assets = release.get("assets")
    if isinstance(assets, list):
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            name = str(asset.get("name") or "")
            asset_match = HEX_SHA256_RE.search(name)
            if asset_match:
                return asset_match.group(0).lower()

    return None


def enforce_release_order(current: Version, current_repo_hash: str, releases: list[GameRelease]) -> None:
    if not releases:
        return
    latest = max(releases, key=lambda item: VersionSortKey(item.version))
    if current.compare(latest.version) < 0:
        raise RuntimeError(
            f"Unity bundleVersion {current.raw} is older than existing game-builds release {latest.version.raw}; "
            "bump Unity bundleVersion before building."
        )

    duplicate_hash_releases = [
        release for release in releases
        if current.compare(release.version) == 0 and release.repo_files_sha256 == current_repo_hash
    ]
    if duplicate_hash_releases:
        existing = duplicate_hash_releases[0]
        raise RuntimeError(
            f"game-builds already has release {existing.tag_name or existing.name} for version {current.raw} "
            f"with repo files SHA-256 {current_repo_hash}; change tracked game files or bump bundleVersion."
        )


class VersionSortKey:
    def __init__(self, version: Version) -> None:
        self.version = version

    def __lt__(self, other: "VersionSortKey") -> bool:
        return self.version.compare(other.version) < 0


def write_outputs(path: str | None, values: dict[str, str]) -> None:
    if not path:
        for key, value in values.items():
            print(f"{key}={value}")
        return
    with open(path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--release-repo", default="Lunavale-Collective/game-builds")
    parser.add_argument("--output", default=os.environ.get("GITHUB_OUTPUT"))
    parser.add_argument("--skip-release-check", action="store_true")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    project_root = args.project_root.resolve()
    version = Version.parse(read_bundle_version(project_root))
    timestamp = datetime.now(timezone.utc)
    current_repo_hash = repo_files_hash(repo_root)
    release_hash_suffix = base62_suffix(current_repo_hash)

    token = os.environ.get("GAME_BUILDS_RELEASE_TOKEN") or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not args.skip_release_check:
        if not token:
            raise RuntimeError("GAME_BUILDS_RELEASE_TOKEN is required to check game-builds releases.")
        enforce_release_order(version, current_repo_hash, fetch_releases(args.release_repo, token))

    outputs = {
        "version": version.raw,
        "is_prerelease": "true" if version.is_prerelease else "false",
        "build_date": timestamp.strftime("%Y-%m-%d"),
        "build_time": timestamp.strftime("%H%M%S"),
        "repo_files_sha256": current_repo_hash,
        "release_hash_suffix": release_hash_suffix,
        "release_tag": f"{version.raw}-{release_hash_suffix}",
        "release_title": f"{version.raw} build {release_hash_suffix}",
        "source_sha": run_git(repo_root, "rev-parse", "HEAD"),
        "unity_editor_version": read_editor_version(project_root),
    }
    write_outputs(args.output, outputs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
