# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Stage a reviewed Orca validator/runtime/resources pair, never a moving nightly."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile
import urllib.request

REVISION = 'f520e9221f220657f752d269ead37dd61e9cb0c3'
VALIDATOR_SHA256 = '337d2bc7c8578ced3e49da06705e34a404a542a8ca5abd32bbf5d243ac3a4032'
EXECUTABLE = 'OrcaSlicer_profile_validator.exe'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def stage_engine(source, runtime, destination, source_output, caches):
    import pefile
    import PySide6
    source, runtime = source.resolve(), runtime.resolve()
    def git(*args):
        return subprocess.check_output(['git', '-C', str(source), *args], text=True).strip()
    if git('rev-parse', 'HEAD') != REVISION or git('status', '--porcelain', '--untracked-files=no'):
        raise ValueError('Orca source must be the clean reviewed revision ' + REVISION)
    executable = runtime / EXECUTABLE
    if digest(executable) != VALIDATOR_SHA256:
        raise ValueError('Unreviewed validator binary: review its build and update the pin explicitly.')
    destination.mkdir(parents=True)
    source_output.mkdir(parents=True, exist_ok=True)
    search = [runtime, Path(PySide6.__file__).parent, Path(sys.base_prefix)]
    pending, copied = [executable], set()
    system = Path(os.environ['SystemRoot']) / 'System32'
    while pending:
        file = pending.pop()
        if file.name.lower() in copied:
            continue
        copied.add(file.name.lower())
        shutil.copy2(file, destination / file.name)
        pe = pefile.PE(str(file))
        try:
            imports = [entry.dll.decode() for entry in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', [])]
            imports += [entry.dll.decode() for entry in getattr(pe, 'DIRECTORY_ENTRY_DELAY_IMPORT', [])]
        finally:
            pe.close()
        for name in imports:
            if name.lower() in copied or name.lower().startswith(('api-ms-', 'ext-ms-')):
                continue
            found = next((folder / name for folder in search if (folder / name).is_file()), None)
            if found:
                pending.append(found)
            elif name.lower().startswith(('msvcp', 'vcruntime')) or not (system / name).is_file():
                raise ValueError('Missing redistributable runtime dependency: ' + name)
    for folder in ('profiles', 'info'):
        shutil.copytree(source / 'resources' / folder, destination / 'resources' / folder)
    shutil.copy2(source / 'LICENSE.txt', destination / 'LICENSE.txt')
    shutil.copy2(Path(__file__).with_name('ORCA-ENGINE-NOTICES.md'), destination)
    # Exact tracked upstream source: excludes the local data_dir, build products
    # and all user data, while retaining upstream recipes and vendored notices.
    upstream_zip = source_output / ('OrcaSlicer-' + REVISION + '-source.zip')
    subprocess.run(['git', '-C', str(source), 'archive', '--format=zip',
                    '--output=' + str(upstream_zip.resolve()), 'HEAD'], check=True)
    required = {'Assimp', 'Blosc', 'Boost', 'Cereal', 'CGAL', 'CURL', 'Eigen',
                'FREETYPE', 'JPEG', 'libnoise', 'NLopt', 'OCCT', 'OpenCV',
                'OpenEXR', 'OpenSSL', 'OpenVDB', 'PNG', 'TBB', 'ZLIB'}
    archived = set()
    dependency_zip = source_output / 'OrcaSlicer-dependency-sources.zip'
    with zipfile.ZipFile(dependency_zip, 'w', zipfile.ZIP_STORED) as archive:
        for name in sorted(required):
            recipe = source / 'deps' / name / (name + '.cmake')
            hashes = set(re.findall(r'SHA256[=\s]+([0-9a-fA-F]{64})', recipe.read_text()))
            files = [p for cache in caches for p in (cache / name).glob('*') if p.is_file()]
            matched = next((p for p in files if digest(p).lower() in {h.lower() for h in hashes}), None)
            if matched is None:
                raise ValueError('Matching source cache is required for Orca dependency: ' + name)
            archive.write(matched, name + '/' + matched.name)
            archived.add(name)
    # Orca carries a prebuilt LGPL GMP 5.0.1 DLL; include the matching GNU source.
    gmp_source = source_output / 'gmp-5.0.1.tar.bz2'
    with urllib.request.urlopen('https://ftp.gnu.org/gnu/gmp/gmp-5.0.1.tar.bz2', timeout=60) as response, gmp_source.open('wb') as output:
        shutil.copyfileobj(response, output)
    manifest = dict(version='2.5.0-dev', revision=REVISION, validator_sha256=VALIDATOR_SHA256,
                    resources_revision=REVISION, source_archives=[upstream_zip.name, dependency_zip.name, gmp_source.name],
                    files={p.relative_to(destination).as_posix(): digest(p)
                           for p in destination.rglob('*') if p.is_file()})
    (destination / 'engine-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('Bundled fixed Orca engine:', len(copied), 'runtime files; matching source resources')
    return manifest
