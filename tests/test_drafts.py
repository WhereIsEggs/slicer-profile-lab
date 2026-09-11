import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from profilelab.drafts import create_draft, load_drafts, save_override
from profilelab.resolver import ProfileResolver


class DraftTests(unittest.TestCase):
    def setUp(self):
        self.profile = {"name": "Base", "type": "process", "vendor": "Example",
                        "path": "Example/process/base.json", "settings": {"speed": "50"}}
        self.metadata = {"version": "2.4.2", "revision": "a" * 40}
        self.resolver = ProfileResolver([self.profile])

    def test_saved_draft_reopens_with_pinned_values(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            draft = create_draft(root, "My process", self.profile, self.metadata, self.resolver)
            self.profile["settings"]["speed"] = "99"
            drafts, errors = load_drafts(root)
            self.assertEqual(errors, [])
            self.assertEqual(drafts, [draft])
            self.assertEqual(drafts[0]["base_values"]["speed"], "50")
            self.assertEqual(drafts[0]["library"]["revision"], "a" * 40)
            self.assertEqual(drafts[0]["overrides"], {})

    def test_bad_or_duplicate_names_do_not_overwrite(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            for name in (" ", "Base", "Bad\nName"):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    create_draft(root, name, self.profile, self.metadata, self.resolver)
            original = create_draft(root, "My process", self.profile, self.metadata, self.resolver)
            with self.assertRaises(ValueError):
                create_draft(root, "MY PROCESS", self.profile, self.metadata, self.resolver)
            self.assertEqual(load_drafts(root)[0], [original])

    def test_name_is_never_used_as_a_path(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            draft = create_draft(root, "../example", self.profile, self.metadata, self.resolver)
            self.assertEqual([path.name for path in root.iterdir()], [f"{draft['id']}.json"])

    def test_missing_parent_prevents_saving(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            self.profile["settings"]["inherits"] = "Missing"
            with self.assertRaises(ValueError):
                create_draft(root, "My process", self.profile, self.metadata, self.resolver)
            self.assertEqual(list(root.iterdir()), [])

    def test_corrupt_draft_is_reported(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "broken.json").write_text("[]", encoding="utf-8")
            drafts, errors = load_drafts(root)
            self.assertEqual(drafts, [])
            self.assertEqual(len(errors), 1)

    def test_override_reopens_and_reset_preserves_base(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            self.profile["settings"]["speed"] = ["50", "50"]
            draft = create_draft(root, "Custom", self.profile, self.metadata, self.resolver)
            updated = save_override(root, draft, "speed", ["60", "70"])
            reopened = load_drafts(root)[0][0]
            self.assertEqual(reopened["overrides"]["speed"], ["60", "70"])
            self.assertEqual(reopened["base_values"]["speed"], ["50", "50"])
            self.assertEqual(self.profile["settings"]["speed"], ["50", "50"])
            reset = save_override(root, updated, "speed", None, reset=True)
            self.assertEqual(reset["overrides"], {})

    def test_stale_edit_and_type_changes_are_rejected(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            draft = create_draft(root, "Custom", self.profile, self.metadata, self.resolver)
            with self.assertRaises(ValueError):
                save_override(root, draft, "speed", 60)
            updated = save_override(root, draft, "speed", "60")
            with self.assertRaisesRegex(ValueError, "changed since"):
                save_override(root, draft, "speed", "70")
            self.assertEqual(load_drafts(root)[0][0], updated)
