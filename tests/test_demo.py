"""Exercise the actual demo widgets without reading the user's profile folders."""

import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QDialog, QInputDialog, QLabel
    from profilelab.desktop import MainWindow
    from profilelab.desktop_theme import apply_theme
    from profilelab.drafts import load_drafts
    from profilelab.package_preview import PackagePreview, package_groups
    from profilelab.profile_install import read_install_bundle, install_bundle
    from profilelab.setting_editor import SettingDialog
    DESKTOP_AVAILABLE = True
except ImportError:
    DESKTOP_AVAILABLE = False


@unittest.skipUnless(DESKTOP_AVAILABLE, "Install the desktop extra for demo tests")
class DemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        apply_theme(cls.app)

    def setUp(self):
        self.temporary = TemporaryDirectory(prefix="profilelab-demo-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        with patch("profilelab.library_view.read_snapshot", side_effect=AssertionError("Real library accessed")):
            self.window = MainWindow(demo_root=self.root)
        self.window.show()
        self.app.processEvents()
        self.addCleanup(self.window.close)

    def capture(self, name, widget=None):
        folder = os.environ.get("PROFILELAB_DEMO_SCREENSHOTS")
        if folder:
            path = Path(folder)
            path.mkdir(parents=True, exist_ok=True)
            self.app.processEvents()
            self.assertTrue((widget or self.window).grab().save(str(path / name)))

    def create_draft_by_click(self):
        self.dialog_errors = []

        def name_draft():
            dialog = QApplication.activeModalWidget()
            try:
                self.assertIsInstance(dialog, QInputDialog)
                dialog.setTextValue("Workshop Printer")
                dialog.accept()
            except Exception as error:
                self.dialog_errors.append(error)
                if dialog:
                    dialog.reject()

        QTimer.singleShot(0, name_draft)
        QTest.mouseClick(self.window.library.create_button, Qt.MouseButton.LeftButton)
        self.assertEqual(self.dialog_errors, [])
        self.assertEqual(self.window.drafts.drafts[0]["name"], "Workshop Printer")

    def test_complete_click_through_and_package_contents(self):
        self.capture("01-library.png")
        self.create_draft_by_click()
        view = self.window.drafts
        row = next(r for r in range(view.values.rowCount()) if view.values.item(r, 0).data(Qt.ItemDataRole.UserRole) == "retraction_length")
        view.values.scrollToItem(view.values.item(row, 1))
        self.app.processEvents()
        errors = []

        def edit_retraction():
            dialog = QApplication.activeModalWidget()
            try:
                self.assertIsInstance(dialog, SettingDialog)
                labels = [label.text() for label in dialog.findChildren(QLabel)]
                self.assertIn("E0 / Left", labels)
                self.assertIn("E1 / Right", labels)
                dialog.editors[0].setText("1.2")
                dialog.editors[1].setText("1.0")
                self.capture("02-extruder-editor.png", dialog)
                dialog.accept_values()
            except Exception as error:
                errors.append(error)
                if dialog:
                    dialog.reject()

        QTimer.singleShot(0, edit_retraction)
        QTest.mouseClick(view.values.viewport(), Qt.MouseButton.LeftButton, pos=view.values.visualItemRect(view.values.item(row, 1)).center())
        self.assertEqual(errors, [])
        saved = load_drafts(self.root / "drafts")[0][0]
        self.assertEqual(saved["overrides"]["retraction_length"], ["1.2", "1.0"])
        self.assertEqual(saved["base_values"]["retraction_length"], ["0.8", "0.8"])
        self.capture("03-saved-draft.png")

        def confirm_package():
            dialog = QApplication.activeModalWidget()
            try:
                self.assertIsInstance(dialog, PackagePreview)
                self.capture("04-package-preview.png", dialog)
                dialog.accept()
            except Exception as error:
                errors.append(error)
                if dialog:
                    dialog.reject()

        QTimer.singleShot(0, confirm_package)
        QTest.mouseClick(view.prepare_button, Qt.MouseButton.LeftButton)
        self.assertEqual(errors, [])
        self.assertIsNotNone(view.last_package)
        self.assertEqual(view.last_package.name, "Workshop Printer.orca_bundle")
        profiles = read_install_bundle(view.last_package)
        groups = package_groups(profiles)
        self.assertEqual({key: len(value) for key, value in groups.items()},
                         {"Printers": 1, "Filaments": 2, "Processes": 1, "Supporting parents": 6})
        printer = next(p for p in profiles if p["name"] == "Workshop Printer")
        self.assertEqual(printer["retraction_length"], ["1.2", "1.0"])
        for material in groups["Filaments"]:
            profile = next(p for p in profiles if p["name"] == material)
            self.assertEqual(profile["compatible_printers"], ["Workshop Printer"])
        self.assertIn("nothing was installed", view.status.text())
        self.capture("05-package-created.png")
        with self.assertRaisesRegex(ValueError, "fictional demo package"):
            install_bundle(view.last_package, self.root / "would-be-orca")
        self.assertFalse((self.root / "would-be-orca").exists())

    def test_repeat_package_saves_reserve_distinct_names(self):
        self.create_draft_by_click()
        view = self.window.drafts
        with patch.object(PackagePreview, "exec", return_value=QDialog.DialogCode.Accepted):
            view.prepare_package()
            first = view.last_package
            original = first.read_bytes()
            view.prepare_package()
        self.assertEqual(view.last_package.name, "Workshop Printer (2).orca_bundle")
        self.assertEqual(first.read_bytes(), original)

    def test_profile_selectors_use_noneditable_compatible_choices(self):
        self.create_draft_by_click()
        view = self.window.drafts
        for key in ("default_filament_profile", "default_print_profile"):
            row = next(r for r in range(view.values.rowCount()) if view.values.item(r, 0).data(Qt.ItemDataRole.UserRole) == key)
            with patch("profilelab.drafts_view.SettingDialog", wraps=SettingDialog) as factory, patch.object(SettingDialog, "exec", return_value=QDialog.DialogCode.Rejected):
                view.edit_value(row, 1)
            self.assertTrue(factory.call_args.kwargs["choices"])
            self.assertEqual(factory.call_args.kwargs["extruder_slots"], key == "default_filament_profile")

    def test_demo_install_and_download_are_disabled_even_if_called_directly(self):
        with patch("profilelab.drafts_view.install_user_profiles") as install, patch("profilelab.desktop.EngineInstallWorker") as download:
            self.window.drafts.install_package("anything.orca_bundle")
            self.window.start_engine_install()
            self.window.start_user_validation()
            install.assert_not_called()
            download.assert_not_called()
        self.assertIsNone(self.window.worker)

    def test_demo_command_line_starts_and_exits_cleanly(self):
        code = '''
import sys
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
import profilelab.desktop as desktop
original = desktop.MainWindow
class AutoCloseWindow(original):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        QTimer.singleShot(100, QApplication.instance().quit)
desktop.MainWindow = AutoCloseWindow
sys.argv = ["profilelab-desktop", "--demo", "--demo-root", sys.argv[1]]
raise SystemExit(desktop.main())
'''
        result = subprocess.run([sys.executable, "-c", code, str(self.root / "cli-demo")],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.root / "cli-demo" / "examples" / "valid" / "demo-0.json").exists())

    def test_demo_workspace_rejects_real_orca_directory(self):
        from profilelab.demo import initialize_demo
        with patch.dict(os.environ, {"APPDATA": str(self.root)}):
            with self.assertRaisesRegex(ValueError, "outside OrcaSlicer"):
                initialize_demo(self.root / "OrcaSlicer" / "user" / "default")
        self.assertFalse((self.root / "OrcaSlicer").exists())

    def test_cancelled_preview_creates_no_package(self):
        self.create_draft_by_click()
        with patch.object(PackagePreview, "exec", return_value=QDialog.DialogCode.Rejected):
            self.window.drafts.prepare_package()
        self.assertFalse((self.root / "packages").exists())

    def test_setting_filter_and_read_only_keys(self):
        self.create_draft_by_click()
        view = self.window.drafts
        view.setting_search.setText("retraction")
        for row in range(view.values.rowCount()):
            item = view.values.item(row, 0)
            self.assertFalse(item.flags() & Qt.ItemFlag.ItemIsEditable)
            self.assertEqual(view.values.isRowHidden(row), "retraction" not in item.text().casefold())

    def test_bad_numeric_text_does_not_close_or_change_editor(self):
        dialog = SettingDialog("Nozzle diameter", "nozzle_diameter", ["0.4", "0.4"], extruder_slots=True)
        for invalid in ("banana", "-1", "NaN", "0"):
            dialog.editors[0].setText(invalid)
            dialog.accept_values()
            self.assertEqual(dialog.result(), QDialog.DialogCode.Rejected)
            self.assertEqual(dialog.value, ["0.4", "0.4"])
            self.assertTrue(dialog.error.text())
        dialog.close()

    def test_both_real_builtin_check_examples(self):
        for name, expected in (("valid", "Built-in checks passed"), ("missing-parent", "Found 1 profile problem")):
            self.window.check_demo_example(name)
            deadline = time.monotonic() + 15
            while self.window.worker is not None and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(0.005)
            self.assertIsNone(self.window.worker)
            self.assertIn(expected, self.window.summary.text())
        self.window.centralWidget().setCurrentIndex(0)
        self.capture("06-missing-parent-check.png")
