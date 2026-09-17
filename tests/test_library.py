# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
import json
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from profilelab.library import (
    REVISION, catalog_from_archive, install_snapshot, install_validation_resources, read_snapshot,
    search_profiles, snapshot_path,
)


class LibraryTests(unittest.TestCase):
    def make_archive(self, path, entries):
        with zipfile.ZipFile(path, "w") as archive:
            for name, content in entries.items():
                archive.writestr(f"OrcaSlicer-{REVISION}/resources/profiles/{name}",
                                 json.dumps(content))

    def test_catalog_retains_vendor_scope_and_ignores_manifests(self):
        with TemporaryDirectory() as folder:
            archive = Path(folder) / "source.zip"
            self.make_archive(archive, {
                "Vendor.json": {"process_list": [{"sub_path": "process/base.json"}]},
                "Other.json": {"process_list": [{"sub_path": "process/base.json"}]},
                "Vendor/cli_config.json": {"unrelated": True},
                "Vendor/process/base.json": {"name": "Base", "type": "process"},
                "Other/process/base.json": {"name": "Base", "type": "process"},
            })
            catalog = catalog_from_archive(archive)
        self.assertEqual(len(catalog), 2)
        self.assertEqual({p["vendor"] for p in catalog}, {"Vendor", "Other"})
        self.assertEqual(len(search_profiles(catalog, "vendor base", "process")), 1)
        self.assertEqual(search_profiles(catalog, "", "filament"), [])

    def test_unsafe_archive_path_is_rejected(self):
        with TemporaryDirectory() as folder:
            archive = Path(folder) / "source.zip"
            self.make_archive(archive, {"../escape.json": {"name": "Bad", "type": "process"}})
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                catalog_from_archive(archive)

    def test_snapshot_can_be_reopened_offline_and_detects_corruption(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "library"
            archive = Path(folder) / "source.zip"
            self.make_archive(archive, {
                "Vendor.json": {"process_list": [{"sub_path": "process/base.json"}]},
                "Vendor/process/base.json": {"name": "Base", "type": "process"},
            })
            with patch("profilelab.library.urllib.request.urlopen", return_value=archive.open("rb")):
                report = install_snapshot(root)
            self.assertEqual(report["metadata"]["profile_count"], 1)
            with patch("profilelab.library.urllib.request.urlopen", side_effect=AssertionError("Network not allowed")):
                self.assertEqual(install_snapshot(root), report)
            (snapshot_path(root) / "catalog.json").write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "integrity"):
                read_snapshot(root)

    def test_failed_download_does_not_publish_library(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            with patch("profilelab.library.urllib.request.urlopen", side_effect=OSError("offline")):
                with self.assertRaises(OSError):
                    install_snapshot(root)
            self.assertIsNone(read_snapshot(root))
            self.assertEqual(list(root.iterdir()), [])

    def test_validation_resources_are_cached_separately_and_reused(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "library"
            archive = Path(folder) / "source.zip"
            self.make_archive(archive, {
                "Vendor.json": {"process_list": [{"sub_path": "process/base.json"}]},
                "Vendor/process/base.json": {"name": "Base", "type": "process"},
            })
            with zipfile.ZipFile(archive, "a") as zipped:
                zipped.writestr(f"OrcaSlicer-{REVISION}/resources/info/nozzle_info.json", "{}")
            with patch("profilelab.library.urllib.request.urlopen", side_effect=lambda *args, **kwargs: archive.open("rb")):
                install_snapshot(root)
                resources = install_validation_resources(root)
            self.assertTrue((resources / "profiles" / "Vendor.json").is_file())
            self.assertTrue((resources / "info" / "nozzle_info.json").is_file())
            with patch("profilelab.library.urllib.request.urlopen", side_effect=AssertionError("Network not allowed")):
                self.assertEqual(install_validation_resources(root), resources)
