import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import zipfile

from profilelab.engine_installer import _extract_portable


class EngineInstallerTests(unittest.TestCase):
    def test_extracts_the_expected_portable_folder(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "portable.zip"
            with zipfile.ZipFile(archive, "w") as contents:
                contents.writestr("OrcaSlicer/OrcaSlicer.dll", b"runtime")
            payload = _extract_portable(archive, root / "output")
            self.assertTrue((payload / "OrcaSlicer.dll").is_file())

    def test_refuses_unsafe_archive_paths(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "portable.zip"
            with zipfile.ZipFile(archive, "w") as contents:
                contents.writestr("../outside.txt", b"not allowed")
            with self.assertRaisesRegex(ValueError, "Unsafe path"):
                _extract_portable(archive, root / "output")
