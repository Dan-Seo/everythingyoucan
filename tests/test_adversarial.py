"""Concrete adversarial regression cases, not a claim of exhaustive security."""
import os
import shutil
import subprocess
from pathlib import Path, PurePosixPath
import sys
import tempfile
import unittest
from unittest.mock import patch
try:
    from test_verify import verify, config
except ModuleNotFoundError:  # run from the repository root: python -m unittest tests.test_adversarial
    from tests.test_verify import verify, config


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

    @unittest.skipIf(sys.platform == "win32", "Windows file names cannot contain newlines")
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

    def test_metadata_check_ignores_case(self):
        # macOS APFS ignores case, but PurePosixPath comparisons do not; isolate the logic.
        parent = PurePosixPath("/repo/.git")
        for target in ["/repo/.GIT/HEAD", "/repo/.Git", "/REPO/.git/objects/new"]:
            with self.subTest(target=target):
                self.assertTrue(verify._is_within(PurePosixPath(target), parent))
        self.assertFalse(verify._is_within(PurePosixPath("/repo/.github/x"), parent))

    def test_existing_untracked_and_ignored_files_are_protected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True, timeout=10)
            (root / ".gitignore").write_text(".env\n")
            for name in [".env", "untracked.txt"]:
                (root / name).write_text("keep")
                with self.subTest(name=name), self.assertRaises(ValueError):
                    verify.checked_report_path(root / name, root, root / "config.json")
                self.assertEqual((root / name).read_text(), "keep")

    def test_previous_report_may_be_rewritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); report = root / "out" / "report.json"
            subprocess.run(["git", "init", "-q", str(root)], check=True, timeout=10)
            verify.write_report(report, verify.run_gates(config(), root))
            self.assertEqual(verify.checked_report_path(report, root, root / "config.json"),
                             report)

    def test_nan_report_does_not_replace_old_report(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"; path.write_text("old")
            with self.assertRaises(ValueError): verify.write_report(path, {"x": float("nan")})
            self.assertEqual(path.read_text(), "old")
            self.assertEqual(list(path.parent.iterdir()), [path])


@unittest.skipUnless(sys.platform == "win32", "Windows path and process semantics")
class WindowsAdversarialTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="verify attacks ")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_report_namespace_cannot_write_git_hook(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True, timeout=10)
        hook = self.root / ".git" / "hooks" / "pre-commit"
        try:
            target = verify.checked_report_path("\\\\?\\" + str(hook), self.root,
                                                self.root / "config.json")
        except ValueError:
            pass
        else:
            verify.write_report(target, {"version": 1, "status": "passed"})
        self.assertFalse(hook.exists(), "extended path wrote a report inside .git")

    def test_ambiguous_windows_report_paths_are_rejected(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True, timeout=10)
        hook = str(self.root / ".git" / "hooks" / "pre-commit")
        targets = ["\\\\?\\" + hook, "\\\\.\\" + hook,
                   "\\\\?\\GLOBALROOT\\??\\" + hook,
                   "\\\\localhost\\" + hook[0] + "$" + hook[2:]]
        targets += [str(self.root / part / "hooks" / "pre-commit") for part in
                    (".git.", ".git ", ".git. .", ".git::$INDEX_ALLOCATION",
                     ".git:$I30:$INDEX_ALLOCATION")]
        for target in targets:
            with self.subTest(target=target), self.assertRaises(ValueError):
                verify.checked_report_path(target, self.root, self.root / "config.json")

    def test_existing_file_aliases_are_protected(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True, timeout=10)
        source = self.root / "source.txt"; source.write_text("keep")
        for target in [str(source) + ".", str(source) + " ", str(source) + "::$DATA",
                       "\\\\?\\" + str(source), "\\\\.\\" + str(source)]:
            with self.subTest(target=target), self.assertRaises(ValueError):
                verify.checked_report_path(target, self.root, self.root / "config.json")
        self.assertEqual(source.read_text(), "keep")

    def test_short_git_alias_is_protected(self):
        import ctypes
        subprocess.run(["git", "init", "-q", str(self.root)], check=True, timeout=10)
        short = ctypes.create_unicode_buffer(32768)
        length = ctypes.windll.kernel32.GetShortPathNameW(str(self.root / ".git"), short,
                                                        len(short))
        self.assertGreater(length, 0)
        self.assertLess(length, len(short))
        with self.assertRaises(ValueError):
            verify.checked_report_path(Path(short.value) / "hooks" / "pre-commit",
                                       self.root, self.root / "config.json")

    def test_bare_command_ignores_caller_cwd(self):
        caller = self.root / "caller"; caller.mkdir()
        bindir = self.root / "bin"; bindir.mkdir()
        marker = self.root / "hijacked"
        shutil.copyfile(Path(os.environ["SystemRoot"]) / "System32" / "cmd.exe",
                        caller / "tool.exe")
        (bindir / "tool.cmd").write_text("@exit /b 0\n")
        value = config(); value["gates"][0]["argv"] = ["tool", "/c", "mkdir", marker.name]
        previous = Path.cwd()
        with patch.dict(os.environ, {"PATH": os.pathsep.join(("", ".", str(bindir))),
                                     "PATHEXT": ".EXE;.BAT;.CMD"}):
            os.environ.pop("NoDefaultCurrentDirectoryInExePath", None)
            try:
                os.chdir(caller)
                report = verify.run_gates(value, self.root)
            finally:
                os.chdir(previous)
        self.assertFalse(marker.exists(), "the caller's planted tool.exe ran")
        self.assertEqual(report["status"], "passed")

    def test_missing_path_command_does_not_fall_back_to_cwd(self):
        caller = self.root / "caller"; caller.mkdir()
        bindir = self.root / "bin"; bindir.mkdir()
        shutil.copyfile(Path(os.environ["SystemRoot"]) / "System32" / "cmd.exe",
                        caller / "missing-tool.exe")
        marker = self.root / "hijacked"
        value = config()
        value["gates"][0]["argv"] = ["missing-tool", "/c", f'echo hijacked>"{marker}"']
        previous = Path.cwd()
        with patch.dict(os.environ, {"PATH": str(bindir),
                                     "NoDefaultCurrentDirectoryInExePath": "1"}):
            try:
                os.chdir(caller)
                report = verify.run_gates(value, self.root)
            finally:
                os.chdir(previous)
        self.assertFalse(marker.exists(), "CreateProcess fell back to the caller's executable")
        self.assertEqual(report["gates"][0]["status"], "launch_error")
        self.assertEqual(report["gates"][1]["status"], "not_run")

    def test_git_metadata_query_ignores_caller_cwd(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True, timeout=10)
        caller = self.root / "caller"; caller.mkdir()
        shutil.copyfile(Path(os.environ["SystemRoot"]) / "System32" / "where.exe",
                        caller / "git.exe")
        previous = Path.cwd()
        try:
            os.chdir(caller)
            target = verify.checked_report_path(self.root / "report.json", self.root,
                                                self.root / "config.json")
        finally:
            os.chdir(previous)
        self.assertEqual(target, self.root / "report.json")

    def test_batch_metacharacters_cannot_inject_commands(self):
        for extension in (".cmd", ".bat"):
            tool = self.root / ("tool" + extension)
            tool.write_text("@rem inert tool\n")
            marker = self.root / ("injected" + extension)
            value = config()
            value["gates"][0]["argv"] = [str(tool), f"x&echo,INJECTED>{marker.name}"]
            report = verify.run_gates(value, self.root)
            with self.subTest(extension=extension):
                self.assertFalse(marker.exists(), "an injected second command ran")
                self.assertEqual(report["gates"][0]["status"], "launch_error")
                self.assertEqual(report["gates"][1]["status"], "not_run")

    def test_batch_risky_arguments_are_rejected_before_launch(self):
        tool = self.root / "tool.cmd"; tool.write_text("@exit /b 0\n")
        for char in '&|<>^()%!"\r\n':
            value = config(); value["gates"][0]["argv"] = [str(tool), "x" + char + "y"]
            with self.subTest(char=repr(char)), patch.object(verify.subprocess, "run") as run:
                report = verify.run_gates(value, self.root)
                run.assert_not_called()
                self.assertEqual(report["gates"][0]["status"], "launch_error")

    def test_batch_path_aliases_cannot_bypass_argument_check(self):
        tool = self.root / "tool.cmd"; tool.write_text("@rem inert tool\n")
        for index, suffix in enumerate((".", " ", "::$DATA")):
            marker = self.root / f"injected{index}"
            value = config()
            value["gates"][0]["argv"] = [str(tool) + suffix,
                                        f"x&echo,INJECTED>{marker.name}"]
            report = verify.run_gates(value, self.root)
            with self.subTest(suffix=suffix):
                self.assertFalse(marker.exists(), "a batch path alias allowed injection")
                self.assertEqual(report["gates"][0]["status"], "launch_error")

    def test_batch_executable_path_cannot_expand_environment_variables(self):
        tool = self.root / "tool%VERIFY_INJECTION%.cmd"; tool.write_text("@exit /b 0\n")
        marker = self.root / "injected"
        (self.root / "tool-expanded.cmd").write_text(f"@echo injected>{marker.name}\n")
        value = config(); value["gates"][0]["argv"] = [str(tool)]
        with patch.dict(os.environ, {"VERIFY_INJECTION": "-expanded"}):
            report = verify.run_gates(value, self.root)
        self.assertFalse(marker.exists(), "cmd.exe expanded the executable's file name")
        self.assertEqual(report["gates"][0]["status"], "launch_error")

    def test_safe_batch_arguments_and_paths_with_spaces_still_work(self):
        for extension in (".cmd", ".bat"):
            tool = self.root / ("tool" + extension)
            tool.write_text('@if not "%~1" == "hello world" exit /b 7\n@exit /b 0\n')
            for command in (str(tool), tool.name, tool.stem):
                value = config(); value["gates"][0]["argv"] = [command, "hello world"]
                with self.subTest(command=command), patch.dict(os.environ,
                        {"PATH": str(self.root), "NoDefaultCurrentDirectoryInExePath": "1"}):
                    report = verify.run_gates(value, self.root)
                    self.assertEqual(report["status"], "passed")

    def test_windows_path_lookup_ignores_extensionless_shell_wrappers(self):
        (self.root / "tool").write_text("#!/bin/sh\nexit 7\n")
        (self.root / "tool.cmd").write_text("@exit /b 0\n")
        value = config(); value["gates"][0]["argv"] = ["tool"]
        for pathext in (".EXE;.BAT;.CMD;", ""):
            with self.subTest(pathext=pathext), patch.dict(os.environ,
                    {"PATH": str(self.root), "PATHEXT": pathext}):
                report = verify.run_gates(value, self.root)
                self.assertEqual(report["status"], "passed")


if __name__ == "__main__":
    unittest.main()
