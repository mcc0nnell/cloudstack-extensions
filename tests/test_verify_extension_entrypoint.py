import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "tools" / "verify_extension_entrypoint.py"
spec = importlib.util.spec_from_file_location("verify_extension_entrypoint", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class VerifyExtensionEntrypointTest(unittest.TestCase):
    def test_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "extension.py"
            payload = b"print('extension')\n"
            path.write_bytes(payload)
            expected = hashlib.sha512(payload).hexdigest()
            result = module.verify(path, expected)
            self.assertTrue(result["verified"])
            self.assertEqual("match", result["reason"])

    def test_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "extension.py"
            path.write_text("changed\n")
            result = module.verify(path, "0" * 128)
            self.assertFalse(result["verified"])
            self.assertEqual("checksum_mismatch", result["reason"])

    def test_invalid_expected_digest(self):
        result = module.verify(Path("unused"), "abc")
        self.assertFalse(result["verified"])
        self.assertEqual("invalid_expected_sha512", result["reason"])

    def test_missing_entrypoint(self):
        result = module.verify(Path("missing-extension.py"), "0" * 128)
        self.assertFalse(result["verified"])
        self.assertEqual("entrypoint_not_found", result["reason"])


if __name__ == "__main__":
    unittest.main()
