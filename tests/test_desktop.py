import os
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import psutil
    from PySide6.QtWidgets import QApplication
    from profilelab.desktop import MainWindow, folder_picker_start
    from profilelab.library_view import LibraryView
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

    def test_background_check_displays_valid_result(self):
        self.run_check("valid_parent")
        self.assertIn("No problems found", self.window.summary.text())

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
