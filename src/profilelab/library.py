# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""An immutable, release-pinned public profile library, separate from user data."""

import hashlib
import json
import os
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

VERSION = "2.4.2"
REVISION = "8500fcdccaa10b5099ac20d252af3a7c560046f1"
SOURCE = "https://github.com/OrcaSlicer/OrcaSlicer"
ARCHIVE_URL = f"https://codeload.github.com/OrcaSlicer/OrcaSlicer/zip/{REVISION}"
MAX_DOWNLOAD = 1024 * 1024 * 1024
MAX_JSON = 8 * 1024 * 1024


def check_library_updates():
    """Check official stable releases without replacing a pinned snapshot."""
    request = urllib.request.Request(
        'https://api.github.com/repos/OrcaSlicer/OrcaSlicer/releases/latest',
        headers={'User-Agent': 'SlicerProfileLab/0.1', 'Accept': 'application/vnd.github+json'},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        release = json.loads(response.read(1024 * 1024))
    import re
    tag = release.get('tag_name', '')
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', tag)
    if not match or release.get('prerelease') or release.get('draft'):
        raise ValueError('GitHub returned an unrecognized stable release.')
    latest = '.'.join(match.groups())
    if tuple(map(int, match.groups())) > tuple(map(int, VERSION.split('.'))):
        return (f'OrcaSlicer {latest} is available. Profile Lab currently supports the {VERSION} library. '
                'This newer library is not enabled yet; compatibility needs to be verified. Your library and drafts are unchanged.')
    return (f'Your supported {VERSION} library is up to date with the latest stable release ({latest}). '
            'This checks releases, not unreleased changes on GitHub.')


def library_home() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local" / "share")))
    return base / "SlicerProfileLab" / "libraries"


def snapshot_path(root: Path) -> Path:
    return root / f"orca-{VERSION}-{REVISION[:12]}"


def validation_resources_path(root: Path) -> Path:
    """A read-only source-shaped tree for Orca's own validation engine."""
    return snapshot_path(root) / "validation_resources"


def read_snapshot(root: Path) -> dict | None:
    folder = snapshot_path(root)
    if not folder.exists():
        return None
    metadata = json.loads((folder / "source.json").read_text(encoding="utf-8"))
    payload = (folder / "catalog.json").read_bytes()
    if metadata.get("revision") != REVISION or metadata.get("version") != VERSION:
        raise ValueError("The local library does not match the supported release.")
    if hashlib.sha256(payload).hexdigest() != metadata.get("catalog_sha256"):
        raise ValueError("The local library failed its integrity check.")
    catalog = json.loads(payload)
    return {"metadata": metadata, "profiles": catalog}


def catalog_from_archive(archive_path: Path) -> list[dict]:
    """Read JSON in memory; never extract arbitrary archive paths to disk."""
    catalog = []
    documents = {}
    seen = set()
    total = 0
    prefix = f"OrcaSlicer-{REVISION}/resources/profiles/"
    with zipfile.ZipFile(archive_path) as archive:
        for entry in archive.infolist():
            if not entry.filename.startswith(prefix) or not entry.filename.endswith(".json"):
                continue
            relative = entry.filename[len(prefix):]
            path = PurePosixPath(relative)
            if path.is_absolute() or ".." in path.parts or "\\" in relative:
                raise ValueError("Unsafe profile path in downloaded archive.")
            if relative in seen:
                raise ValueError("Duplicate file in downloaded archive.")
            seen.add(relative)
            total += entry.file_size
            if entry.file_size > MAX_JSON or total > 256 * 1024 * 1024:
                raise ValueError("Profile library exceeds the supported size.")
            profile = json.loads(archive.read(entry).decode("utf-8-sig"))
            if not isinstance(profile, dict):
                raise ValueError(f"Profile file is not an object: {relative}")
            documents[relative] = profile
    # Vendor manifests distinguish actual profiles from auxiliary JSON tables.
    profile_paths = set()
    for name, manifest in documents.items():
        if "/" in name:
            continue
        vendor = name[:-5]
        for category in ("machine_model_list", "machine_list", "filament_list", "process_list"):
            for item in manifest.get(category, []):
                sub_path = item["sub_path"]
                parts = PurePosixPath(sub_path).parts
                if PurePosixPath(sub_path).is_absolute() or ".." in parts or "\\" in sub_path:
                    raise ValueError("Unsafe profile path in vendor manifest.")
                profile_paths.add(f"{vendor}/{sub_path}")
    for relative in sorted(profile_paths):
            path = PurePosixPath(relative)
            if relative not in documents:
                raise ValueError(f"Vendor manifest references a missing file: {relative}")
            profile = documents[relative]
            kind = profile.get("type")
            if kind not in {"machine", "machine_model", "filament", "process"}:
                raise ValueError(f"Unrecognized profile type: {relative}")
            name = profile.get("name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"Profile has no usable name: {relative}")
            catalog.append({
                "name": name, "type": kind, "vendor": path.parts[0],
                "path": relative, "parent": profile.get("inherits", ""),
                "template": profile.get("instantiation") not in {"true", True},
                "settings": profile,
            })
    if not catalog:
        raise ValueError("The archive contained no supported profiles.")
    return sorted(catalog, key=lambda item: (item["vendor"], item["type"], item["name"], item["path"]))


def install_snapshot(root: Path, progress=lambda message: None) -> dict:
    """Download once; stage and verify before publishing the version directory."""
    existing = read_snapshot(root)
    if existing is not None:
        return existing
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="download-", dir=root) as temporary:
        staging = Path(temporary)
        archive_path = staging / "source.zip"
        progress("Downloading the official 2.4.2 source snapshot…")
        request = urllib.request.Request(ARCHIVE_URL, headers={"User-Agent": "SlicerProfileLab/0.1"})
        digest = hashlib.sha256()
        received = 0
        with urllib.request.urlopen(request, timeout=60) as response, archive_path.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                received += len(chunk)
                if received > MAX_DOWNLOAD:
                    raise ValueError("The download exceeds the supported size.")
                digest.update(chunk)
                output.write(chunk)
                progress(f"Downloading library source: {received // (1024 * 1024)} MB")
        progress("Checking and indexing profile files…")
        catalog = catalog_from_archive(archive_path)
        prepared = staging / "prepared"
        prepared.mkdir()
        payload = json.dumps(catalog, ensure_ascii=False).encode("utf-8")
        (prepared / "catalog.json").write_bytes(payload)
        metadata = {
            "version": VERSION, "revision": REVISION, "source": SOURCE,
            "download_url": ARCHIVE_URL, "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "archive_sha256": digest.hexdigest(), "catalog_sha256": hashlib.sha256(payload).hexdigest(),
            "profile_count": len(catalog),
            "license_url": f"{SOURCE}/blob/{REVISION}/LICENSE.txt",
        }
        (prepared / "source.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        # Rename on the same drive publishes only a fully built snapshot.
        destination = snapshot_path(root)
        if not destination.exists():
            prepared.rename(destination)
    return read_snapshot(root)


def install_validation_resources(root: Path, progress=lambda message: None) -> Path:
    """Cache only trusted upstream resources needed to compose user-profile checks."""
    snapshot = read_snapshot(root)
    if snapshot is None:
        install_snapshot(root, progress)
    destination = validation_resources_path(root)
    if destination.is_dir():
        return destination
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="validation-source-", dir=root) as temporary:
        staging = Path(temporary)
        archive_path = staging / "source.zip"
        progress("Preparing the matching system library for validation…")
        request = urllib.request.Request(ARCHIVE_URL, headers={"User-Agent": "SlicerProfileLab/0.1"})
        with urllib.request.urlopen(request, timeout=60) as response, archive_path.open("wb") as output:
            received = 0
            while chunk := response.read(1024 * 1024):
                received += len(chunk)
                if received > MAX_DOWNLOAD:
                    raise ValueError("The download exceeds the supported size.")
                output.write(chunk)
        prepared = staging / "validation_resources"
        profiles = prepared / "profiles"
        prefix = f"OrcaSlicer-{REVISION}/resources/"
        with zipfile.ZipFile(archive_path) as archive:
            for entry in archive.infolist():
                if entry.is_dir() or not entry.filename.startswith(prefix):
                    continue
                relative = PurePosixPath(entry.filename[len(prefix):])
                if relative.is_absolute() or ".." in relative.parts or "\\" in str(relative):
                    raise ValueError("Unsafe resource path in downloaded archive.")
                # The profile tree and nozzle data are what the validation executable uses.
                if not (relative.parts[0] == "profiles" or relative == PurePosixPath("info/nozzle_info.json")):
                    continue
                target = prepared.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(entry))
        if not profiles.is_dir():
            raise ValueError("The downloaded source has no profile tree.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        prepared.rename(destination)
    return destination


def search_profiles(profiles: list[dict], query: str = "", kind: str = "") -> list[dict]:
    words = query.casefold().split()
    return [item for item in profiles
            if (not kind or item["type"] == kind)
            and all(word in f"{item['name']} {item['vendor']} {item['parent']}".casefold()
                    for word in words)]
