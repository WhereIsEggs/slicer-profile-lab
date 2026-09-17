# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
import os
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import psutil
    from PySide6.QtWidgets import QApplication
    from profilelab.desktop import MainWindow, default_user_profile_folder, folder_picker_start
    from profilelab.library_view import LibraryView
    from profilelab.drafts_view import DraftsView
    from profilelab.setting_editor import SettingDialog, display_value
    from PySide6.QtCore import Qt
    from profilelab.orca_status import OrcaStatus, get_orca_status, require_orca_closed
    DESKTOP_AVAILABLE = True
except ImportError:
    DESKTOP_AVAILABLE = False


@unittest.skipUnless(DESKTOP_AVAILABLE, "Install the desktop extra to test the window")
class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temporary = TemporaryDirectory(prefix="profilelab-desktop-test-")
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.isolation = ExitStack()
        self.addCleanup(self.isolation.close)
        self.isolation.enter_context(patch("profilelab.library_view.library_home", return_value=root / "library"))
        self.isolation.enter_context(patch("profilelab.library_view.drafts_home", return_value=root / "drafts"))
        self.isolation.enter_context(patch("profilelab.drafts_view.drafts_home", return_value=root / "drafts"))
        with patch("profilelab.desktop.get_orca_status", return_value=OrcaStatus.CLOSED):
            self.window = MainWindow()

    def tearDown(self):
        if self.window.worker is not None:
            self.window.worker.wait()
            self.app.processEvents()
        self.window.close()

    def run_check(self, fixture):
        self.window.folder.setText(str(Path(__file__).parent / "fixtures" / fixture))
        self.window.start_validation()
        self.assertFalse(self.window.check.isEnabled())
        deadline = time.monotonic() + 10
        while self.window.worker is not None and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.005)
        self.assertIsNone(self.window.worker)
        self.assertTrue(self.window.check.isEnabled())

    def test_background_check_reports_when_engine_needs_a_complete_tree(self):
        self.run_check("valid_parent")
        self.assertIn("Full validation is not confirmed", self.window.summary.text())
        self.assertIn("complete system profile library", self.window.results.toPlainText())

    def test_list_editor_keeps_text_types_and_plain_display(self):
        dialog = SettingDialog("Flow", "flow", ["70%", "70%"])
        self.assertEqual(display_value(["70%", "70%"]), "70% · 70%")
        dialog.editors[0].setText("80%")
        dialog.accept_values()
        self.assertEqual(dialog.value, ["80%", "70%"])
        dialog.close()

    def test_draft_keys_are_read_only_and_click_edit_saves(self):
        from profilelab.drafts import create_draft, load_drafts
        from profilelab.resolver import ProfileResolver
        with TemporaryDirectory() as folder:
            root = Path(folder)
            profile = {"name": "Base", "type": "process", "vendor": "Example",
                       "path": "Example/base.json", "settings": {"flow": ["70%", "70%"]}}
            create_draft(root, "Custom", profile, {"version": "2.4.2", "revision": "a" * 40}, ProfileResolver([profile]))
            view = DraftsView(root=root)
            view.list.setCurrentRow(0)
            self.assertFalse(view.values.item(0, 0).flags() & Qt.ItemFlag.ItemIsEditable)
            with patch("profilelab.drafts_view.SettingDialog") as editor:
                editor.return_value.exec.return_value = 1
                editor.return_value.value = ["80%", "70%"]
                view.edit_value(0, 0)
                editor.assert_not_called()
                view.edit_value(0, 1)
            self.assertEqual(load_drafts(root)[0][0]["overrides"]["flow"], ["80%", "70%"])
            self.assertTrue(view.values.item(0, 1).font().bold())
            view.close()

    def test_create_and_reopen_draft_from_library(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            library = LibraryView(root=root / "library", draft_root=root / "drafts")
            library.show_snapshot({"metadata": {"version": "2.4.2", "revision": "a" * 40,
                                                 "downloaded_at": "2026-09-11"},
                "profiles": [{"name": "Base", "type": "process", "vendor": "Example",
                              "parent": "", "path": "Example/process/base.json", "template": False,
                              "settings": {"name": "Base", "speed": "50"}}]})
            library.table.selectRow(0)
            self.assertTrue(library.create_button.isEnabled())
            with patch("profilelab.library_view.QInputDialog.getText", return_value=("My process", True)):
                library.make_draft()
            drafts = DraftsView(root=root / "drafts")
            drafts.list.setCurrentRow(0)
            self.assertEqual(drafts.drafts[0]["name"], "My process")
            self.assertEqual(drafts.values.item(0, 1).text(), "50")
            library.close()
            drafts.close()

    def test_picker_starts_at_orca_folder_and_preserves_selection(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            orca = root / "OrcaSlicer"
            orca.mkdir()
            selected = root / "selected"
            selected.mkdir()
            with patch.dict(os.environ, {"APPDATA": folder}):
                self.assertEqual(folder_picker_start(""), str(orca))
                self.assertEqual(folder_picker_start(str(selected)), str(selected))
                with patch("profilelab.desktop.QFileDialog.getExistingDirectory", return_value="") as picker:
                    self.window.choose_folder()
                    self.assertEqual(picker.call_args.args[2], str(orca))
                    self.assertEqual(self.window.folder.text(), "")

    def test_picker_falls_back_when_orca_is_not_installed(self):
        with TemporaryDirectory() as folder:
            with patch.dict(os.environ, {"APPDATA": folder}):
                self.assertEqual(folder_picker_start(""), str(Path.home()))

    def test_picker_prefers_default_user_profiles(self):
        with TemporaryDirectory() as folder:
            default = Path(folder) / "OrcaSlicer" / "user" / "default"
            default.mkdir(parents=True)
            with patch.dict(os.environ, {"APPDATA": folder}):
                self.assertEqual(folder_picker_start(""), str(default))

    def test_check_my_profiles_uses_default_folder_and_engine_workspace(self):
        from profilelab.engine_validator import EngineValidationResult
        with TemporaryDirectory() as folder:
            default = Path(folder) / "OrcaSlicer" / "user" / "default"
            default.mkdir(parents=True)
            (default / "profile.json").write_text('{"name":"Custom"}', encoding="utf-8")
            with patch.dict(os.environ, {"APPDATA": folder}), \
                 patch("profilelab.desktop.validation_engine_resources", return_value=Path(folder) / "resources") as resources, \
                 patch("profilelab.desktop.run_orca_engine_for_user_profiles", return_value=EngineValidationResult("passed", "Orca's own engine check passed.")) as engine:
                self.assertEqual(default_user_profile_folder(), default)
                self.window.start_user_validation()
                deadline = time.monotonic() + 10
                while self.window.worker is not None and time.monotonic() < deadline:
                    self.app.processEvents()
                    time.sleep(0.005)
            self.assertIsNone(self.window.worker)
            resources.assert_called_once()
            engine.assert_called_once_with(Path(folder) / "resources", default)
            self.assertIn("Validation checks passed", self.window.summary.text())

    def test_background_check_displays_error_and_clears_stale_result(self):
        self.run_check("missing_parent")
        self.assertIn("is missing parent", self.window.results.toPlainText())
        self.window.folder.setText("")
        self.assertEqual(self.window.results.toPlainText(), "")
        self.assertFalse(self.window.check.isEnabled())

    def test_read_failure_is_not_shown_as_success(self):
        with patch("profilelab.desktop.validate_folder", side_effect=PermissionError("denied")):
            self.run_check("valid_parent")
        self.assertEqual(self.window.summary.text(), "Check could not finish")

    def test_orca_process_detection(self):
        process = Mock()
        process.name.return_value = "OrcaSlicer.exe"
        with patch("profilelab.orca_status.psutil.process_iter", return_value=[process]):
            self.assertEqual(get_orca_status(), OrcaStatus.RUNNING)

    def test_unreadable_process_means_unknown(self):
        process = Mock()
        process.name.side_effect = psutil.AccessDenied(1)
        with patch("profilelab.orca_status.psutil.process_iter", return_value=[process]):
            self.assertEqual(get_orca_status(), OrcaStatus.UNKNOWN)

    def test_install_guard_blocks_running_and_unknown(self):
        for status in (OrcaStatus.RUNNING, OrcaStatus.UNKNOWN):
            with self.subTest(status=status):
                with patch("profilelab.orca_status.get_orca_status", return_value=status):
                    with self.assertRaises(RuntimeError):
                        require_orca_closed()
        with patch("profilelab.orca_status.get_orca_status", return_value=OrcaStatus.CLOSED):
            require_orca_closed()

    def test_library_search_and_type_filter(self):
        with TemporaryDirectory() as folder:
            view = LibraryView(root=Path(folder))
            view.show_snapshot({
                "metadata": {"version": "2.4.2", "revision": "a" * 40,
                             "downloaded_at": "2026-09-11"},
                "profiles": [
                    {"name": "Standard", "type": "process", "vendor": "Example",
                     "parent": "Base", "path": "Example/process/standard.json",
                     "template": False, "settings": {"name": "Standard"}},
                    {"name": "PLA", "type": "filament", "vendor": "Example",
                     "parent": "", "path": "Example/filament/pla.json",
                     "template": False, "settings": {"name": "PLA"}},
                ],
            })
            view.search.setText("base")
            self.assertEqual(view.table.rowCount(), 1)
            view.table.selectRow(0)
            self.assertIn("Standard", view.details.toPlainText())
            view.kind.setCurrentIndex(view.kind.findData("filament"))
            self.assertEqual(view.table.rowCount(), 0)
            self.assertEqual(view.details.toPlainText(), "")
            view.close()

    def test_resolved_settings_display_and_clear_after_broken_parent(self):
        with TemporaryDirectory() as folder:
            view = LibraryView(root=Path(folder))
            base = {"name": "Base", "type": "process", "vendor": "Example",
                    "parent": "", "path": "Example/base.json", "template": True,
                    "settings": {"name": "Base", "speed": "50"}}
            child = {"name": "Child", "type": "process", "vendor": "Example",
                     "parent": "Base", "path": "Example/child.json", "template": False,
                     "settings": {"name": "Child", "inherits": "Base", "speed": "60"}}
            broken = {"name": "Broken", "type": "process", "vendor": "Example",
                      "parent": "Missing", "path": "Example/broken.json", "template": False,
                      "settings": {"name": "Broken", "inherits": "Missing"}}
            view.show_snapshot({"metadata": {"version": "2.4.2", "revision": "a" * 40,
                                             "downloaded_at": "2026-09-11"},
                                "profiles": [base, child, broken]})
            view.table.selectRow(1)
            self.assertEqual(view.settings_table.item(0, 1).text(), "60")
            self.assertEqual(view.settings_table.item(0, 2).text(), "Overridden here")
            view.table.selectRow(2)
            self.assertEqual(view.settings_table.rowCount(), 0)
            self.assertIn("Cannot resolve", view.resolution_status.text())
            view.close()
