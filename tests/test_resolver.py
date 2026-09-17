# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 WhereIsEggs (Profile Lab contributions).
# See LICENSE.txt and NOTICE.md for license, warranty and upstream attribution.
import unittest

from profilelab.resolver import ProfileResolver, ResolutionError


def profile(name, parent="", vendor="Example", kind="process", **settings):
    return {"name": name, "vendor": vendor, "type": kind,
            "path": f"{vendor}/{kind}/{name}.json",
            "settings": {"name": name, "type": kind, "inherits": parent, **settings}}


class ResolverTests(unittest.TestCase):
    def test_multilevel_values_and_provenance(self):
        base = profile("Base", speed="50", layer="0.2", enabled=True, items=[1, 2])
        middle = profile("Middle", "Base", speed="60")
        child = profile("Child", "Middle", layer="0.2", enabled=False, items=[], extra="")
        result = ProfileResolver([base, middle, child]).resolve(child)
        self.assertEqual(result["speed"].value, "60")
        self.assertEqual(result["speed"].source_name, "Middle")
        self.assertEqual(result["speed"].status, "Inherited")
        self.assertEqual(result["layer"].status, "Same as parent")
        self.assertEqual(result["enabled"].status, "Overridden here")
        self.assertFalse(result["enabled"].value)
        self.assertEqual(result["items"].value, [])
        self.assertEqual(result["extra"].status, "Defined here")
        self.assertNotIn("name", result)
        self.assertNotIn("inherits", result)
        result["items"].value.append(3)
        self.assertEqual(child["settings"]["items"], [])

    def test_vendor_and_type_scope(self):
        base = profile("Base", speed="50")
        unrelated = profile("Base", vendor="Other", speed="99")
        wrong_type = profile("Base", kind="filament", speed="100")
        child = profile("Child", "Base")
        self.assertEqual(ProfileResolver([base, unrelated, wrong_type, child]).resolve(child)["speed"].value, "50")

    def test_shared_filament_library_fallback(self):
        base = profile("PLA", vendor="OrcaFilamentLibrary", kind="filament", temperature=["200"])
        child = profile("Custom PLA", "PLA", kind="filament")
        self.assertEqual(ProfileResolver([base, child]).resolve(child)["temperature"].source_vendor, "OrcaFilamentLibrary")

    def test_missing_parent_does_not_return_partial_values(self):
        child = profile("Child", "Missing", speed="50")
        with self.assertRaisesRegex(ResolutionError, "not found"):
            ProfileResolver([child]).resolve(child)

    def test_ambiguous_parent_is_rejected(self):
        child = profile("Child", "Base")
        with self.assertRaisesRegex(ResolutionError, "ambiguous"):
            ProfileResolver([profile("Base"), profile("Base"), child]).resolve(child)

    def test_cycle_is_rejected(self):
        first = profile("A", "B")
        second = profile("B", "A")
        with self.assertRaisesRegex(ResolutionError, "cycle"):
            ProfileResolver([first, second]).resolve(first)
