# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Isolated install/reinstall/uninstall acceptance check; never use a real app directory."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import winreg

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('installer', type=Path)
    parser.add_argument('--previous-installer', type=Path, help='Optional Alpha 1 installer for an upgrade check')
    args = parser.parse_args()
    key = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\{2F601791-C674-48F3-A66A-42D84CC0E178}_is1'
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key):
            raise SystemExit('An alpha is already installed; use a separate Windows test account.')
    except FileNotFoundError:
        pass
    parent = ROOT / 'artifacts' / 'installer-tests'
    parent.mkdir(exist_ok=True)
    sandbox = Path(tempfile.mkdtemp(prefix='lifecycle-', dir=parent)).resolve()
    app = sandbox / 'app'
    assert app.is_relative_to(parent.resolve())
    environment = os.environ.copy()
    environment['PATH'] = str(Path(os.environ['SystemRoot']) / 'System32')
    for name in ('PYTHONPATH', 'PYTHONHOME', 'PROFILELAB_ORCA_VALIDATOR'):
        environment.pop(name, None)

    def run(arguments):
        subprocess.run([str(p) for p in arguments], check=True, timeout=600,
                       env=environment, creationflags=subprocess.CREATE_NO_WINDOW)

    try:
        if args.previous_installer:
            run([args.previous_installer.resolve(), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                 '/NOICONS', '/TASKS=', '/DIR=' + str(app), '/LOG=' + str(sandbox / 'previous-install.log')])
        for stage in ('install', 'reinstall'):
            run([args.installer.resolve(), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                 '/NOICONS', '/TASKS=', '/DIR=' + str(app), '/LOG=' + str(sandbox / (stage + '.log'))])
            report = sandbox / (stage + '-smoke.json')
            run([app / 'SlicerProfileLab.exe', '--smoke-test', report])
            assert json.loads(report.read_text())['passed']
    finally:
        uninstaller = app / 'unins000.exe'
        if uninstaller.is_file():
            run([uninstaller, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                 '/LOG=' + str(sandbox / 'uninstall.log')])
    assert not (app / 'SlicerProfileLab.exe').exists()
    print('Install, reinstall, packaged checks and uninstall passed:', sandbox)


if __name__ == '__main__':
    main()
