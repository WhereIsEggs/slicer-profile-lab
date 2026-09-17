# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Install Orca's optional validator engine into Profile Lab's private cache."""

import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
from tempfile import TemporaryDirectory
import urllib.request
import zipfile

from profilelab.engine_validator import engine_home, validator_path


RELEASE_URL = "https://api.github.com/repos/OrcaSlicer/OrcaSlicer/releases/tags/nightly-builds"
PORTABLE_NAME = "OrcaSlicer_Windows_x64_nightly_portable.zip"
VALIDATOR_NAME = "OrcaSlicer_profile_validator_Windows_nightly.exe"
MAX_DOWNLOAD = 512 * 1024 * 1024


def _release_assets() -> dict[str, dict]:
    request = urllib.request.Request(RELEASE_URL, headers={"User-Agent": "SlicerProfileLab/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        release = json.load(response)
    return {asset["name"]: asset for asset in release["assets"]}


def _download_verified(asset: dict, destination: Path, progress) -> None:
    expected = asset.get("digest", "").removeprefix("sha256:").casefold()
    if len(expected) != 64:
        raise ValueError("OrcaSlicer did not publish a SHA-256 checksum for this download.")
    request = urllib.request.Request(asset["browser_download_url"], headers={"User-Agent": "SlicerProfileLab/0.1"})
    digest = hashlib.sha256()
    received = 0
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            received += len(chunk)
            if received > MAX_DOWNLOAD:
                raise ValueError("The Orca download is larger than Profile Lab supports.")
            digest.update(chunk)
            output.write(chunk)
            progress(f"Downloading Orca engine: {received // (1024 * 1024)} MB")
    if digest.hexdigest() != expected:
        raise ValueError("The Orca download did not match its published checksum.")


def _extract_portable(archive_path: Path, destination: Path) -> Path:
    with zipfile.ZipFile(archive_path) as archive:
        for entry in archive.infolist():
            relative = PurePosixPath(entry.filename)
            if relative.is_absolute() or ".." in relative.parts or "\\" in entry.filename:
                raise ValueError("Unsafe path in the official Orca archive.")
            target = destination.joinpath(*relative.parts)
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(entry))
    payload = destination / "OrcaSlicer"
    if not payload.is_dir():
        raise ValueError("The official Orca archive has an unexpected layout.")
    return payload


def install_engine(progress=lambda message: None) -> Path:
    """Download verified official files, then publish only a complete runtime."""
    existing = validator_path()
    if existing.is_file():
        return existing
    root = engine_home().parent
    root.mkdir(parents=True, exist_ok=True)
    assets = _release_assets()
    try:
        portable = assets[PORTABLE_NAME]
        validator = assets[VALIDATOR_NAME]
    except KeyError as error:
        raise ValueError("The current Orca nightly release is missing a required Windows file.") from error
    with TemporaryDirectory(prefix="install-", dir=root) as temporary:
        staging = Path(temporary)
        progress("Downloading the verified Orca runtime…")
        portable_zip = staging / "orca-portable.zip"
        _download_verified(portable, portable_zip, progress)
        progress("Downloading the verified Orca validator…")
        validator_file = staging / "OrcaSlicer_profile_validator.exe"
        _download_verified(validator, validator_file, progress)
        progress("Preparing the Orca engine…")
        payload = _extract_portable(portable_zip, staging / "portable")
        shutil.copy2(validator_file, payload / validator_file.name)
        target = engine_home()
        if target.exists():
            raise ValueError("An incomplete Orca engine folder is already present. Remove it before reinstalling.")
        payload.rename(target)
    if not validator_path().is_file():
        raise ValueError("The Orca engine installation could not be verified.")
    return validator_path()
