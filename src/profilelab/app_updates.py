# SPDX-License-Identifier: AGPL-3.0-only
"""Explicitly invoked release checks and verified downloads; no scheduler."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.request

REPOSITORY = 'https://github.com/WhereIsEggs/slicer-profile-lab'
API = 'https://api.github.com/repos/WhereIsEggs/slicer-profile-lab/releases?per_page=100'


def version_key(value):
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)(?:[-.]?(alpha|beta|rc|a|b)[.-]?(\d+))?', value)
    if not match:
        raise ValueError('Unsupported release version')
    major, minor, patch, stage, number = match.groups()
    return (int(major), int(minor), int(patch),
            {None: 3, 'rc': 2, 'beta': 1, 'b': 1, 'alpha': 0, 'a': 0}[stage], int(number or 0))


@dataclass(frozen=True)
class Update:
    tag: str
    filename: str
    url: str
    checksums_url: str
    page: str


def asset_url(url):
    if not isinstance(url, str) or not url.startswith(REPOSITORY + '/releases/download/'):
        raise ValueError('Unexpected release download location.')
    return url


def read_url(url, limit):
    request = urllib.request.Request(url, headers={'User-Agent': 'SlicerProfileLab-manual-update'})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError('Release response is too large.')
    return data


def choose_update(releases, current):
    current_key = version_key(current)
    candidates = []
    for release in releases:
        if release.get('draft'):
            continue
        tag = release.get('tag_name', '')
        try:
            key = version_key(tag)
        except (ValueError, TypeError):
            continue
        # Alpha/beta users can follow previews; stable users get stable only.
        if key <= current_key or (current_key[3] == 3 and (release.get('prerelease') or key[3] < 3)):
            continue
        assets = release.get('assets', [])
        installers = [a for a in assets if re.fullmatch(r'SlicerProfileLab-[\w.-]+-windows-x64-setup\.exe', a.get('name', ''))]
        sums = [a for a in assets if a.get('name') == 'SHA256SUMS.txt']
        if len(installers) != 1 or len(sums) != 1:
            continue
        installer = installers[0]
        try:
            asset_version = installer['name'][len('SlicerProfileLab-'):-len('-windows-x64-setup.exe')]
            if version_key(asset_version) != key:
                continue
        except ValueError:
            continue
        candidates.append((key, Update(tag, installer['name'], asset_url(installer['browser_download_url']),
                                       asset_url(sums[0]['browser_download_url']), REPOSITORY + '/releases')))
    return max(candidates, key=lambda item: item[0])[1] if candidates else None


def check_update(current):
    releases = json.loads(read_url(API, 8 * 1024 * 1024))
    if not isinstance(releases, list):
        raise ValueError('GitHub returned an unexpected response.')
    return choose_update(releases, current)


def download_update(update, root=None, progress=lambda value: None):
    checksums = read_url(asset_url(update.checksums_url), 65536).decode('utf-8')
    matches = re.findall(r'^([a-fA-F0-9]{64})\s+\*?' + re.escape(update.filename) + r'\s*$', checksums, re.MULTILINE)
    if len(matches) != 1 or Path(update.filename).name != update.filename:
        raise ValueError('The release does not have an unambiguous installer checksum.')
    root = Path(root) if root else Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'SlicerProfileLab' / 'updates'
    root.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix='download-', dir=root))
    partial = folder / 'installer.part'
    target = folder / update.filename
    try:
        digest, size = hashlib.sha256(), 0
        request = urllib.request.Request(asset_url(update.url), headers={'User-Agent': 'SlicerProfileLab-manual-update'})
        with urllib.request.urlopen(request, timeout=30) as response, partial.open('xb') as output:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > 1024 * 1024 * 1024:
                    raise ValueError('Installer exceeds the download size limit.')
                output.write(chunk)
                digest.update(chunk)
                progress(size)
        if digest.hexdigest() != matches[0].lower():
            raise ValueError('Installer verification failed. Nothing was installed; try again later.')
        partial.rename(target)
        return target
    except Exception:
        partial.unlink(missing_ok=True)
        folder.rmdir()
        raise
