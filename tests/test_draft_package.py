from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from profilelab.draft_package import export_draft_package, prepare_draft_profiles
from profilelab.profile_install import install_bundle


class DraftPackageTests(unittest.TestCase):
    def test_empty_public_compatibility_strings_are_normalized_in_copies(self):
        drafts = self.drafts()
        drafts[1]["base_chain"] = [{"vendor": "Example", "type": "process", "name": "Base", "path": "base.json", "settings": {"compatible_printers": "", "compatible_prints": "", "compatible_printers_condition": "nozzle_diameter[0]==0.4"}}]
        before = deepcopy(drafts)
        profiles, _ = prepare_draft_profiles("printer", drafts)
        parent = next(p for p in profiles if p["name"] == "Base - Example base")
        self.assertEqual(parent["compatible_printers"], [])
        self.assertEqual(parent["compatible_prints"], [])
        self.assertEqual(parent["compatible_printers_condition"], "nozzle_diameter[0]==0.4")
        self.assertEqual(drafts, before)

    def test_frozen_parents_and_material_identity_survive_library_removal(self):
        drafts = self.drafts()
        chain = [{"vendor": "Example", "type": "filament", "name": "Source PLA", "path": "pla.json",
                  "settings": {"name": "Source PLA", "inherits": "Material Base", "setting_id": "system-only"}},
                 {"vendor": "Example", "type": "filament", "name": "Material Base", "path": "base.json",
                  "settings": {"filament_id": "OF0UJcb6", "filament_type": ["PETG"]}}]
        drafts[2]["base_chain"] = chain
        drafts[2]["base_values"]["filament_type"] = ["PETG"]
        before = deepcopy(drafts)
        profiles, _ = prepare_draft_profiles("printer", drafts)
        material = next(p for p in profiles if p["name"].startswith("Fictional PLA - Fictional"))
        self.assertEqual(material["filament_id"], "OF0UJcb6")
        self.assertEqual(material["inherits"], "Source PLA - Example base")
        self.assertTrue(all("setting_id" not in p for p in profiles))
        self.assertEqual(drafts, before)

    def test_missing_frozen_parent_fails_instead_of_flattening(self):
        drafts = self.drafts()
        drafts[0]["base_chain"] = [{"vendor": "Example", "type": "machine", "name": "Source", "path": "source.json", "settings": {"inherits": "Missing"}}]
        with self.assertRaisesRegex(ValueError, "Parent.*not found"):
            prepare_draft_profiles("printer", drafts)

    def test_older_draft_cannot_recover_parents_from_changed_library(self):
        drafts = self.drafts()
        drafts[0]["base"] = {"vendor": "Example", "name": "Old", "path": "old.json"}
        with self.assertRaisesRegex(ValueError, "original library revision"):
            prepare_draft_profiles("printer", drafts)

    def test_material_identity_changes_are_not_silently_reused(self):
        drafts = self.drafts()
        drafts[2]["overrides"]["filament_type"] = ["ABS"]
        with self.assertRaisesRegex(ValueError, "new product identity"):
            prepare_draft_profiles("printer", drafts)

    def drafts(self):
        return [
            {"id": "printer", "name": "Fictional Printer", "type": "machine", "library": {"version": "2.4.2"}, "base_values": {"nozzle_diameter": ["0.4"], "default_print_profile": "Fictional Process", "default_filament_profile": ["Fictional PLA"]}, "overrides": {}},
            {"id": "process", "name": "Fictional Process", "type": "process", "library": {"version": "2.4.2"}, "base_values": {"layer_height": "0.2", "compatible_printers": ["Fictional Printer"]}, "overrides": {"layer_height": "0.16"}},
            {"id": "filament", "name": "Fictional PLA", "type": "filament", "library": {"version": "2.4.2"}, "base_values": {"filament_type": ["PLA"], "compatible_printers": ["Fictional Printer"]}, "overrides": {}},
        ]

    def test_drafts_to_bundle_to_clean_install_preserves_values(self):
        drafts = self.drafts()
        before = deepcopy(drafts)
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "fictional.orca_bundle"
            export_draft_package("printer", drafts, None, bundle)
            self.assertEqual(drafts, before)
            with patch("profilelab.profile_install.require_orca_closed"):
                paths = install_bundle(bundle, root / "user" / "default")
            self.assertEqual({p.parent.name for p in paths}, {"machine", "process", "filament"})
            profiles = {p["type"]: p for p in (json.loads(path.read_text()) for path in paths)}
            prefix = "_local/" + paths[0].parent.parent.name + "/"
            self.assertEqual(profiles["process"]["layer_height"], "0.16")
            self.assertEqual(profiles["process"]["compatible_printers"], [prefix + profiles["machine"]["name"]])
            self.assertEqual(profiles["machine"]["default_print_profile"], prefix + profiles["process"]["name"])
            self.assertEqual(profiles["machine"]["default_filament_profile"], [prefix + profiles["filament"]["name"]])
            self.assertNotEqual(profiles["process"]["name"], "Fictional Process")
            self.assertNotEqual(profiles["filament"]["name"], "Fictional PLA")
            self.assertTrue(all(not p["inherits"] for p in profiles.values()))

    def test_missing_material_blocks_preparation(self):
        with self.assertRaisesRegex(ValueError, "Fictional PLA.*missing"):
            prepare_draft_profiles("printer", self.drafts()[:2])

    def test_compatible_printer_lists_do_not_expand_printer_package(self):
        drafts = self.drafts()
        drafts[1]["base_values"]["compatible_printers"] = ["Original Printer", "Another Printer"]
        drafts[2]["base_values"]["compatible_printers"] = ["Original Printer", "Third Printer"]
        before = deepcopy(drafts)
        with TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "single-printer.orca_bundle"
            profiles = export_draft_package("printer", drafts, None, bundle)
            from profilelab.profile_install import read_install_bundle
            reopened = read_install_bundle(bundle)
        self.assertEqual(len(profiles), 3)
        self.assertEqual([p["name"] for p in reopened if p["type"] == "machine"], ["Fictional Printer"])
        for profile in reopened:
            if profile["type"] != "machine":
                self.assertEqual(profile["compatible_printers"], ["Fictional Printer"])
        self.assertEqual(drafts, before)

    def test_printer_mapping_does_not_discard_compatibility_conditions(self):
        drafts = self.drafts()
        drafts[2]["base_values"]["compatible_printers_condition"] = 'printer_model=="Original"'
        profiles, _ = prepare_draft_profiles("printer", drafts)
        filament = next(p for p in profiles if p["type"] == "filament")
        self.assertEqual(filament["compatible_printers_condition"], 'printer_model=="Original"')
        self.assertEqual(filament["compatible_printers"], ["Fictional Printer"])

    def test_library_dependency_is_resolved_with_inherited_values(self):
        drafts = self.drafts()[:2]
        library = [
            {"vendor": "Example", "type": "filament", "name": "Base", "path": "base.json", "settings": {"filament_type": ["PLA"]}},
            {"vendor": "Example", "type": "filament", "name": "Fictional PLA", "path": "pla.json", "settings": {"inherits": "Base", "compatible_printers": ["Fictional Printer"]}},
        ]
        profiles, _ = prepare_draft_profiles("printer", drafts, {"profiles": library, "metadata": {"version": "2.4.2"}})
        material = next(p for p in profiles if p["type"] == "filament" and p.get("instantiation") != "false")
        self.assertEqual(material["filament_type"], ["PLA"])
        self.assertEqual(material["inherits"], "Fictional PLA - Example base")
        parent = next(p for p in profiles if p["name"] == material["inherits"])
        self.assertEqual(parent["inherits"], "Base - Example base")
