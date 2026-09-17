# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Offline packaged-app acceptance check using temporary fictional data only."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import traceback
import sys


def run_smoke(report_path):
    report = {'passed': False}
    try:
        with TemporaryDirectory(prefix='profilelab-packaged-smoke-') as folder:
            root = Path(folder)
            # Set before importing desktop: no reads/writes to the real app cache.
            os.environ['LOCALAPPDATA'] = str(root / 'local')
            os.environ['APPDATA'] = str(root / 'roaming')
            os.environ.pop('PROFILELAB_ORCA_VALIDATOR', None)
            from PySide6.QtCore import QTimer
            from PySide6.QtWidgets import QApplication
            import psutil
            from profilelab import __version__
            from profilelab.legal import legal_root
            assert 'GNU AFFERO GENERAL PUBLIC LICENSE' in (legal_root() / 'LICENSE.txt').read_text()
            assert 'WhereIsEggs' in (legal_root() / 'NOTICE.md').read_text()
            from profilelab.desktop import MainWindow
            from profilelab.desktop_theme import apply_theme
            from profilelab.profile_sets import new_set, add_copy, prepare_set, save_set, load_sets
            from profilelab.orca_bundle import export_orca_bundle
            from profilelab.user_sharing import share_prepared_package
            from profilelab.validation import validate_folder
            from profilelab.user_install import exportable_profiles
            app = QApplication([])
            apply_theme(app)
            window = MainWindow()
            window.show()
            app.processEvents()
            from unittest.mock import patch
            from profilelab.update_dialog import UpdateDialog
            with patch('profilelab.update_dialog.check_update') as update_check:
                updates = UpdateDialog(window)
                updates.show()
                app.processEvents()
                assert updates.worker is None
                update_check.assert_not_called()
                updates.close()
            report['manual_updates_only'] = True
            data = new_set('Packaged smoke test')
            add_copy(data, 'machine', 'Fictional test printer', {'nozzle_diameter': ['0.4']}, '2.4.2')
            add_copy(data, 'filament', 'Fictional PLA', {'filament_diameter': ['1.75']}, '2.4.2')
            add_copy(data, 'process', 'Fictional process', {'layer_height': '0.2'}, '2.4.2')
            data['defaults'] = dict(filaments=['Fictional PLA'], process='Fictional process')
            save_set(root / 'sets', data)
            assert load_sets(root / 'sets') == [data]
            profiles = prepare_set(data)
            package = root / 'smoke.orca_bundle'
            export_orca_bundle(profiles, [(p['type'], p['name']) for p in profiles], package)
            share = share_prepared_package(package)
            assert share.is_file() and len(exportable_profiles(package)) == 3
            check = root / 'check'
            check.mkdir()
            (check / 'root.json').write_text('{"name":"Root","type":"process"}', encoding='utf-8')
            assert validate_folder(check).is_valid
            assert psutil.Process().pid > 0
            report.update(version=__version__, tabs=window.centralWidget().count(),
                          qt_platform=app.platformName(), shared_profiles=3)
            if getattr(sys, 'frozen', False):
                from profilelab.engine_validator import run_orca_engine_for_user_profiles, validation_engine_resources
                from unittest.mock import patch
                user = root / 'native-user'
                user.mkdir()
                with patch('urllib.request.urlopen', side_effect=AssertionError('Offline validation attempted a download')):
                    engine = run_orca_engine_for_user_profiles(validation_engine_resources(), user, 90)
                assert engine.status == 'passed', engine.message + '\n' + engine.details
                report['offline_engine'] = engine.status
                (user / 'broken.json').write_text(json.dumps({'name': 'Broken test', 'type': 'machine',
                                                             'inherits': 'Missing smoke-test parent'}))
                with patch('urllib.request.urlopen', side_effect=AssertionError('Validation attempted a download')):
                    rejected = run_orca_engine_for_user_profiles(validation_engine_resources(), user, 90)
                assert rejected.status == 'failed' and 'Missing smoke-test parent' in rejected.details
                report['broken_parent_rejected'] = True
            QTimer.singleShot(200, app.quit)
            app.exec()
            window.close()
            report['passed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    Path(report_path).write_text(json.dumps(report, indent=2), encoding='utf-8')
    return 0 if report['passed'] else 1
