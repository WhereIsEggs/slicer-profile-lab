# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Build a per-user alpha installer from an allowlisted app payload, not the workspace."""
import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import distribution, version
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
from source_archive import write_project_source, write_complete_source

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from profilelab import __version__


def run(command):
    environment = os.environ.copy()
    # Never collect unrelated Qt/ICU/OpenSSL DLLs from developer tools on PATH.
    environment['PATH'] = os.pathsep.join((str(Path(sys.executable).parent),
                                         str(Path(sys.base_prefix)),
                                         str(Path(os.environ['SystemRoot']) / 'System32'),
                                         os.environ['SystemRoot']))
    subprocess.run([str(p) for p in command], cwd=ROOT, env=environment, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--iscc', type=Path, required=True, help='Installed Inno Setup 6 compiler')
    args = parser.parse_args()
    if sys.platform != 'win32' or sys.maxsize <= 2**32:
        raise SystemExit('Build on 64-bit Windows with 64-bit Python.')
    if not args.iscc.is_file():
        raise SystemExit('Installer compiler was not found.')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    release = ROOT / 'artifacts' / 'releases' / f'{__version__}-{stamp}'
    work = ROOT / 'artifacts' / 'build' / stamp
    assets = work / 'assets'
    release.mkdir(parents=True)
    (assets / 'docs').mkdir(parents=True)
    for relative in ('README.md', 'Real Workflow Guide.md', 'docs/alpha-testing.md',
                     'docs/upstream-variant-audit.md', 'docs/windows-release.md',
                     'docs/licensing.md', 'LICENSE.txt', 'NOTICE.md'):
        destination = assets / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    shutil.copy2(ROOT / 'packaging/THIRD-PARTY-NOTICES.md', assets)
    licenses = assets / 'licenses'
    licenses.mkdir()
    dependencies = {}
    for name in ('PySide6', 'PySide6_Essentials', 'PySide6_Addons', 'shiboken6', 'psutil', 'pyinstaller'):
        dist = distribution(name)
        dependencies[name] = version(name)
        target = licenses / name
        target.mkdir()
        (target / 'METADATA.txt').write_text(dist.read_text('METADATA') or '', encoding='utf-8')
        for file in dist.files or []:
            if any('license' in p.lower() or 'copying' in p.lower() for p in file.parts):
                source = Path(dist.locate_file(file))
                if source.is_file():
                    shutil.copy2(source, target / source.name)
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if not python_license.is_file():
        raise RuntimeError('Python license file missing; do not ship incomplete notices.')
    shutil.copy2(python_license, licenses / 'Python-LICENSE.txt')
    # Ship matching LGPL component source beside the binaries, not just a promise
    # to fetch it later. These archives also preserve third-party attribution.
    sources = assets / 'dependency-sources'
    sources.mkdir()
    cache = ROOT / 'artifacts' / 'source-cache'
    cache.mkdir(exist_ok=True)
    source_urls = [
        'https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.2-src/pyside-setup-everywhere-src-6.11.2.tar.xz',
        *['https://download.qt.io/archive/qt/6.11/6.11.2/submodules/' + module + '-everywhere-src-6.11.2.tar.xz'
          for module in ('qtbase', 'qtsvg', 'qtimageformats')],
    ]
    for url in source_urls:
        cached = cache / url.rsplit('/', 1)[1]
        included = ROOT / 'dependency-sources' / cached.name
        if not cached.exists() and included.is_file():
            shutil.copy2(included, cached)
        with urllib.request.urlopen(url + '.sha256', timeout=60) as response:
            expected = response.read().decode().split()[0]
        if not cached.is_file() or hashlib.sha256(cached.read_bytes()).hexdigest() != expected:
            with urllib.request.urlopen(url, timeout=60) as response, cached.open('wb') as output:
                shutil.copyfileobj(response, output)
        if hashlib.sha256(cached.read_bytes()).hexdigest() != expected:
            raise RuntimeError('Source archive checksum mismatch: ' + url)
        shutil.copy2(cached, sources / cached.name)
    # The psutil extension is required by the app; include its exact source too.
    with urllib.request.urlopen('https://pypi.org/pypi/psutil/' + version('psutil') + '/json', timeout=60) as response:
        psutil_release = json.load(response)
    sdist = next(item for item in psutil_release['urls'] if item['packagetype'] == 'sdist')
    cached = cache / Path(sdist['filename']).name
    expected = sdist['digests']['sha256']
    included = ROOT / 'dependency-sources' / cached.name
    if not cached.exists() and included.is_file():
        shutil.copy2(included, cached)
    if not cached.is_file() or hashlib.sha256(cached.read_bytes()).hexdigest() != expected:
        with urllib.request.urlopen(sdist['url'], timeout=60) as response, cached.open('wb') as output:
            shutil.copyfileobj(response, output)
    if hashlib.sha256(cached.read_bytes()).hexdigest() != expected:
        raise RuntimeError('psutil source archive checksum mismatch')
    shutil.copy2(cached, sources / cached.name)
    # Wheels omit some open-source license texts; collect exact upstream Qt texts.
    for name in ('LGPL-3.0-only.txt', 'GPL-3.0-only.txt', 'Qt-GPL-exception-1.0.txt'):
        url = 'https://raw.githubusercontent.com/qt/qtbase/v6.11.2/LICENSES/' + name
        with urllib.request.urlopen(url, timeout=60) as response:
            content = response.read()
        (licenses / name).write_bytes(content)
    if (ROOT / '.git').exists():
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip())
    else:
        origin = ROOT / 'build-info.json'
        revision = json.loads(origin.read_text()).get('revision') if origin.is_file() else None
        dirty = None  # No git history: do not claim this rebuild is unchanged.
    info = dict(version=__version__, built_utc=stamp, python=sys.version,
                revision=revision, dirty=dirty, license='AGPL-3.0-only',
                dependencies=dependencies, publisher='WhereIsEggs')
    (assets / 'build-info.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    project_source = assets / 'profilelab-source.zip'
    write_project_source(ROOT, project_source, info)
    release_source = release / f'SlicerProfileLab-{__version__}-source.zip'
    write_complete_source(project_source, sources, release_source)
    run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--onedir', '--windowed', '--noupx',
         '--additional-hooks-dir', ROOT / 'packaging/hooks',
         '--name', 'SlicerProfileLab', '--paths', ROOT / 'src', '--distpath', release / 'app',
         '--workpath', work / 'pyinstaller', '--specpath', work,
         '--add-data', str(assets) + ';.', ROOT / 'packaging/launch.py'])
    payload = release / 'app' / 'SlicerProfileLab'
    allowed_qt = {'Qt6Core.dll', 'Qt6Gui.dll', 'Qt6Widgets.dll', 'Qt6Network.dll', 'Qt6Svg.dll'}
    collected_qt = {p.name for p in (payload / '_internal' / 'PySide6').glob('Qt6*.dll')}
    if collected_qt - allowed_qt:
        raise RuntimeError('Unreviewed Qt modules collected: ' + str(collected_qt - allowed_qt))
    report = release / 'packaged-smoke.json'
    subprocess.run([str(payload / 'SlicerProfileLab.exe'), '--smoke-test', str(report)],
                   cwd=release, timeout=60, check=True)
    if not json.loads(report.read_text())['passed']:
        raise RuntimeError('Packaged smoke test failed; no installer will be compiled.')
    run([args.iscc.resolve(), '/DPayloadDir=' + str(payload), '/DReleaseDir=' + str(release),
         '/DAppVersion=' + __version__, ROOT / 'packaging/installer.iss'])
    setup = release / f'SlicerProfileLab-{__version__}-windows-x64-setup.exe'
    checksums = ''.join(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n'
                        for path in (setup, release_source))
    (release / 'SHA256SUMS.txt').write_text(checksums, encoding='utf-8')
    shutil.copy2(ROOT / 'LICENSE.txt', release)
    shutil.copy2(ROOT / 'NOTICE.md', release)
    shutil.copy2(assets / 'build-info.json', release)
    shutil.copy2(ROOT / 'docs/alpha-testing.md', release / 'START-HERE.md')
    print('Release ready:', release)


if __name__ == '__main__':
    main()
