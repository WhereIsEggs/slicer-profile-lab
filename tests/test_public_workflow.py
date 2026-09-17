# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
"""Opt-in normal desktop workflow using the real cached public library."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@unittest.skipUnless(os.environ.get("PROFILELAB_PUBLIC_LIBRARY_TESTS") == "1", "Opt-in public library desktop test")
class PublicWorkflowTests(unittest.TestCase):
    def test_normal_draft_package_and_install_handlers(self):
        from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
        from profilelab.library import library_home, read_snapshot
        from profilelab.library_view import LibraryView
        from profilelab.drafts_view import DraftsView
        from profilelab.profile_install import read_install_bundle
        from profilelab.package_preview import package_groups
        app = QApplication.instance() or QApplication([])
        snapshot = read_snapshot(library_home())
        with TemporaryDirectory(prefix="profilelab-public-ui-") as temporary:
            root = Path(temporary)
            library = LibraryView(draft_root=root / "drafts", snapshot=snapshot)
            view = DraftsView(root=root / "drafts", snapshot=snapshot, package_root=root / "sharing")
            try:
                self.assertFalse(view.demo_mode)
                # Exercise the normal creation handler, retaining all public records.
                printer = next(p for p in snapshot["profiles"] if p["vendor"] == "Prusa" and p["name"] == "Prusa MK3S 0.4 nozzle")
                from profilelab.drafts import load_drafts
                library.table.selectRow(library.matches.index(printer))
                with patch("profilelab.library_view.QInputDialog.getText", return_value=("Workshop MK3S", True)), patch("profilelab.library_view.QMessageBox.warning") as warning:
                    library.make_draft()
                warning.assert_not_called()
                draft = load_drafts(root / "drafts")[0][0]
                view.refresh(draft["id"])
                with patch("profilelab.drafts_view.PackagePreview.exec", return_value=QDialog.DialogCode.Accepted), patch("profilelab.drafts_view.QMessageBox.question", return_value=QMessageBox.StandardButton.No), patch("profilelab.drafts_view.QMessageBox.warning") as warning:
                    view.prepare_package()
                warning.assert_not_called()
                self.assertEqual(view.last_package.name, "Workshop MK3S.orca_bundle")
                groups = package_groups(read_install_bundle(view.last_package))
                self.assertEqual([len(groups[k]) for k in ("Printers", "Filaments", "Processes")], [1, 1, 1])
                # Only the destination and process guard are isolated; actual installer runs.
                with patch.dict(os.environ, {"APPDATA": str(root / "roaming")}), patch("profilelab.user_install.require_orca_closed"), patch("profilelab.drafts_view.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes), patch("profilelab.drafts_view.QFileDialog.getOpenFileName") as picker, patch("profilelab.drafts_view.QMessageBox.warning") as warning:
                    view.install_package()
                picker.assert_not_called()
                warning.assert_not_called()
                self.assertIn("Installed successfully", view.status.text())
                self.assertIn("Workshop MK3S", view.status.text())
                import json
                installed_root = root / "roaming" / "OrcaSlicer" / "user" / "default"
                self.assertFalse((installed_root / "_local").exists())
                for kind in ("machine", "filament", "process"):
                    files = list((installed_root / kind).glob("*.json"))
                    self.assertEqual(len(files), 1)
                    self.assertEqual(json.loads(files[0].read_text(encoding="utf-8"))["inherits"], "")
            finally:
                view.close()
                library.close()
                app.processEvents()
