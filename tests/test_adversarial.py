"""Concrete adversarial regression cases, not a claim of exhaustive security."""
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_verify import verify, config


class AdversarialTests(unittest.TestCase):
    def test_nonfinite_and_huge_integer_timeouts(self):
        for timeout in [float("nan"), float("inf"), -float("inf"), 10**400]:
            value = config(); value["gates"][0]["timeout_seconds"] = timeout
            with self.assertRaises(ValueError): verify.validate_config(value)

    def test_nested_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text('{"version":1,"gates":[{"name":"a","name":"b"}]}')
            with self.assertRaisesRegex(ValueError, "duplicate"):
                verify.load_config(path)

    def test_deep_json_rejected_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"; path.write_text("["*2000+"0"+"]"*2000)
            with self.assertRaises(ValueError): verify.load_config(path)

    def test_invalid_late_gate_runs_nothing(self):
        value = config(); value["gates"][2]["argv"] = []
        with patch.object(verify.subprocess, "run") as run:
            with self.assertRaises(ValueError): verify.run_gates(value, ".")
            run.assert_not_called()

    def test_metacharacters_are_literal_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); value = config()
            payload = "; echo compromised > marker.txt"
            value["gates"][0]["argv"] = ["{python}", "-c",
                "import sys; assert sys.argv[1] == '; echo compromised > marker.txt'", payload]
            report = verify.run_gates(value, root)
            self.assertEqual(report["status"], "passed")
            self.assertFalse((root / "marker.txt").exists())

    def test_failed_first_gate_never_creates_later_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); value = config()
            value["gates"][0]["argv"] = ["{python}", "-c", "raise SystemExit(1)"]
            value["gates"][1]["argv"] = ["{python}", "-c",
                "from pathlib import Path; Path('marker').write_text('bad')"]
            verify.run_gates(value, root)
            self.assertFalse((root / "marker").exists())

    def test_surrogate_argv_is_rejected_before_any_command(self):
        value = config(); value["gates"][0]["argv"] = ["\ud800"]
        with patch.object(verify.subprocess, "run") as run:
            with self.assertRaises(ValueError): verify.run_gates(value, ".")
            run.assert_not_called()

    def test_git_metadata_is_protected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True, timeout=10)
            for relative in [".git", ".git/HEAD", ".git/config", ".git/objects/new"]:
                with self.subTest(path=relative), self.assertRaises(ValueError):
                    verify.checked_report_path(root / relative, root, root / "config.json")
            result = subprocess.run(["git", "status", "--porcelain"], cwd=root,
                                    capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0)

    def test_external_worktree_metadata_is_protected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "worktree"; root.mkdir()
            metadata = Path(directory) / "metadata"; common = Path(directory) / "common"
            results = [subprocess.CompletedProcess([], 0, stdout=(str(p) + "\n").encode())
                       for p in (metadata, common)]
            for path in [metadata / "HEAD", common / "config"]:
                with patch.object(verify.subprocess, "run", side_effect=results):
                    with self.assertRaises(ValueError):
                        verify.checked_report_path(path, root, root / "config.json")

    def test_real_worktree_with_newline_parent_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo\nnewline"
            worktree = Path(directory) / "worktree"
            def git(*args, cwd=None):
                return subprocess.run(["git", *args], cwd=cwd, check=True,
                                      capture_output=True, timeout=15)
            git("init", "-q", str(root))
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                "commit", "--allow-empty", "-m", "test", cwd=root)
            git("worktree", "add", "--detach", str(worktree), cwd=root)
            gitdir = Path(git("rev-parse", "--git-dir", cwd=worktree).stdout.decode().removesuffix("\n"))
            for target in [root/".git/HEAD", root/".git/config", root/".git/objects/new",
                           gitdir/"HEAD"]:
                with self.subTest(target=target), self.assertRaises(ValueError):
                    verify.checked_report_path(target, worktree, worktree/"config.json")
            git("status", "--porcelain", cwd=worktree)

    def test_nan_report_does_not_replace_old_report(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"; path.write_text("old")
            with self.assertRaises(ValueError): verify.write_report(path, {"x": float("nan")})
            self.assertEqual(path.read_text(), "old")
            self.assertEqual(list(path.parent.iterdir()), [path])


if __name__ == "__main__":
    unittest.main()
