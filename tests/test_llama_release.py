"""Regression tests for resumable runtime and weight downloads."""

import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from jev.runtime.llama_release import fetch


class DownloadTests(unittest.TestCase):
    def test_completed_partial_is_promoted_after_range_not_satisfiable(self):
        content = b"complete download"
        digest = hashlib.sha256(content).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "model.gguf"
            partial = target.with_name(target.name + ".part")
            partial.write_bytes(content)
            error = HTTPError("https://example.test/model", 416, "Range Not Satisfiable", {}, None)
            with patch(
                "jev.runtime.llama_release.urllib.request.urlopen", side_effect=error
            ) as urlopen:
                self.assertEqual(fetch("https://example.test/model", target, digest), target)

            self.assertEqual(target.read_bytes(), content)
            self.assertFalse(partial.exists())
            self.assertEqual(urlopen.call_count, 1)

    def test_invalid_partial_restarts_after_range_not_satisfiable(self):
        content = b"complete download"
        digest = hashlib.sha256(content).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "model.gguf"
            partial = target.with_name(target.name + ".part")
            partial.write_bytes(b"invalid trailing data" * 2)
            error = HTTPError("https://example.test/model", 416, "Range Not Satisfiable", {}, None)
            response = io.BytesIO(content)
            response.status = 200
            response.headers = {"Content-Length": str(len(content))}

            def urlopen_request(request, timeout):
                if request.get_header("Range"):
                    raise error
                return response

            with patch(
                "jev.runtime.llama_release.urllib.request.urlopen", side_effect=urlopen_request
            ) as urlopen:
                self.assertEqual(fetch("https://example.test/model", target, digest), target)

            self.assertEqual(target.read_bytes(), content)
            self.assertFalse(partial.exists())
            self.assertEqual(urlopen.call_count, 2)


if __name__ == "__main__":
    unittest.main()
