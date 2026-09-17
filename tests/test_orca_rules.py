import unittest

from profilelab.orca_rules import check_system_setting_id, system_setting_id, system_filament_id
from profilelab.bundle_contract import strict_json, scope_profiles


class OrcaRulesTests(unittest.TestCase):
    def test_setting_ids_match_official_cpp_golden_vectors(self):
        vectors = [
            ("Afinia", "filament", "Afinia ABS @Afinia H400", "TL34qSVkppBvMvgH"),
            ("Afinia", "process", "0.20mm Standard @Afinia H400", "FzmtNsy7XQvpd7w0"),
            ("Afinia", "machine", "Afinia H400 0.4 nozzle", "r4FZagW0S8uoaJPd"),
            ("Anycubic", "filament", "Generic PLA @Anycubic Kobra 2", "YIWGGLQ8Oepd30Fv"),
            ("Creality", "process", "0.16mm Optimal @Creality Ender-3 V3", "2Nrbq8PxssUPBLza"),
            ("Elegoo", "machine", "Elegoo Neptune 4 0.4 nozzle", "69QdWuRQwAZk9rFu"),
        ]
        for vendor, kind, name, expected in vectors:
            with self.subTest(name=name):
                self.assertEqual(system_setting_id(vendor, kind, name), expected)

    def test_filament_ids_match_official_snapshot(self):
        self.assertEqual(system_filament_id("Creality", "PLA", "Soleyin Ultra PLA"), "OF02UAVh")
        self.assertEqual(system_filament_id("Polymaker", "PETG", "PolyLite PETG"), "OF0UJcb6")

    def test_system_template_and_bbl_rules(self):
        with self.assertRaises(ValueError):
            check_system_setting_id("Example", {"instantiation": "false", "setting_id": "bad"})
        check_system_setting_id("BBL", {"instantiation": "true", "setting_id": "Greserved"})
        with self.assertRaises(ValueError):
            check_system_setting_id("BBL", {"instantiation": "true"})
        with self.assertRaises(ValueError):
            check_system_setting_id("Example", {"settings_id": "typo"})

    def test_duplicate_keys_and_nonfinite_numbers_are_rejected(self):
        for payload in ('{"name":"A","name":"B"}', '{"nested":{"x":1,"x":2}}', '{"x":NaN}', '{"x":Infinity}'):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                strict_json(payload)

    def test_scope_changes_references_not_expressions_or_names(self):
        profiles = [{"type": "machine", "name": "Printer"},
                    {"type": "filament", "name": "PLA", "compatible_printers": ["Printer", "External"],
                     "compatible_printers_condition": 'printer_model=="Printer"'}]
        scoped = scope_profiles(profiles, "example")
        self.assertEqual(scoped[1]["compatible_printers"], ["_local/example/Printer", "External"])
        self.assertEqual(scoped[1]["compatible_printers_condition"], profiles[1]["compatible_printers_condition"])
        self.assertEqual(scope_profiles(scoped, "example", unqualify=True), profiles)
