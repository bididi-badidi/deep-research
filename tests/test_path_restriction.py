import unittest
from pathlib import Path
import shutil
from utils import get_safe_path


class TestPathRestriction(unittest.TestCase):
    def setUp(self):
        self.workspace = Path("/tmp/gemini-test-workspace").resolve()
        if self.workspace.exists():
            shutil.rmtree(self.workspace)
        self.workspace.mkdir(parents=True)

    def tearDown(self):
        if self.workspace.exists():
            shutil.rmtree(self.workspace)

    def test_valid_paths(self):
        # Simple relative path
        safe = get_safe_path("data.txt", self.workspace)
        self.assertEqual(safe, self.workspace / "data.txt")

        # Path within subdirectory
        (self.workspace / "subdir").mkdir()
        safe = get_safe_path("subdir/test.md", self.workspace)
        self.assertEqual(safe, self.workspace / "subdir" / "test.md")

    def test_escape_attempts(self):
        # Simple traversal
        with self.assertRaises(PermissionError) as cm:
            get_safe_path("../secret.txt", self.workspace)
        self.assertIn("escapes the workspace", str(cm.exception))

        # Absolute path attempt (outside)
        with self.assertRaises(PermissionError) as cm:
            get_safe_path("/etc/passwd", self.workspace)
        self.assertIn("escapes the workspace", str(cm.exception))

        # Complex traversal
        with self.assertRaises(PermissionError) as cm:
            get_safe_path("subdir/../../etc/shadow", self.workspace)
        self.assertIn("escapes the workspace", str(cm.exception))

    def test_absolute_within_workspace(self):
        # Even if they provide an absolute path, if it resolves inside, it is allowed
        inside_abs = str(self.workspace / "allowed.txt")
        safe = get_safe_path(inside_abs, self.workspace)
        self.assertEqual(safe, self.workspace / "allowed.txt")


if __name__ == "__main__":
    unittest.main()
