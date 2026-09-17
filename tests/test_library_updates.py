import io
import json
import unittest
from unittest.mock import patch

from profilelab.library import check_library_updates


class LibraryUpdateTests(unittest.TestCase):
    def check_release(self, tag):
        response = io.BytesIO(json.dumps({'tag_name': tag, 'prerelease': False, 'draft': False}).encode())
        with patch('profilelab.library.urllib.request.urlopen', return_value=response):
            return check_library_updates()

    def test_current_release(self):
        self.assertIn('up to date', self.check_release('v2.4.2'))

    def test_new_release_does_not_claim_installed(self):
        message = self.check_release('v2.10.0')
        self.assertIn('not enabled yet', message)
        self.assertIn('unchanged', message)

    def test_unknown_release_rejected(self):
        with self.assertRaises(ValueError):
            self.check_release('nightly')
