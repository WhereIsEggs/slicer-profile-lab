# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Create matching release source from explicit project paths, never user caches."""
import hashlib
import json
from pathlib import Path
import zipfile


def project_files(root):
    for name in ('README.md', 'Real Workflow Guide.md', 'pyproject.toml', 'LICENSE.txt',
                 'NOTICE.md', 'Start Profile Lab.cmd', '.gitignore'):
        yield root / name
    for folder in ('src/profilelab', 'packaging', 'docs', 'tests'):
        for path in sorted((root / folder).rglob('*')):
            if (path.is_file() and '__pycache__' not in path.parts
                    and path.suffix in ('.py', '.iss', '.txt', '.md', '.json', '.toml', '.cmd')):
                if path.is_symlink():
                    raise ValueError('Source archives must not follow symlinks: ' + str(path))
                yield path


def write_project_source(root, target, info):
    manifest = {}
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in project_files(root):
            relative = path.relative_to(root).as_posix()
            content = path.read_bytes()
            manifest[relative] = hashlib.sha256(content).hexdigest()
            archive.writestr(relative, content)
        archive.writestr('build-info.json', json.dumps(info, indent=2))
        archive.writestr('source-manifest.json', json.dumps(manifest, indent=2))


def write_complete_source(project_zip, dependency_sources, target):
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        with zipfile.ZipFile(project_zip) as project:
            for name in project.namelist():
                archive.writestr(name, project.read(name))
        for path in sorted(dependency_sources.iterdir()):
            if path.is_file():
                archive.write(path, 'dependency-sources/' + path.name)
