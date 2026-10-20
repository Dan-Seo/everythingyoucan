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
            subprocess.run([verify._command_path("git"), "init", "-q", str(root)], check=True, timeout=10)
            for relative in [".git", ".git/HEAD", ".git/config", ".git/objects/new"]:
                with self.subTest(path=relative), self.assertRaises(ValueError):
                    verify.checked_report_path(root / relative, root, root / "config.json")
            result = subprocess.run([verify._command_path("git"), "status", "--porcelain"], cwd=root,
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
                return subprocess.run([verify._command_path("git"), *args], cwd=cwd, check=True,
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
            subprocess.run([verify._command_path("git"), "init", "-q", str(root)], check=True, timeout=10)
            (root / ".gitignore").write_text(".env\n")
            for name in [".env", "untracked.txt"]:
                (root / name).write_text("keep")
                with self.subTest(name=name), self.assertRaises(ValueError):
                    verify.checked_report_path(root / name, root, root / "config.json")
                self.assertEqual((root / name).read_text(), "keep")

    def test_previous_report_may_be_rewritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); report = root / "out" / "report.json"
            subprocess.run([verify._command_path("git"), "init", "-q", str(root)], check=True, timeout=10)
            verify.write_report(report, verify.run_gates(config(), root))
            self.assertEqual(verify.checked_report_path(report, root, root / "config.json"),
                             report)

    def test_crlf_prefix_cannot_masquerade_as_previous_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); report = root / "notes.txt"
            subprocess.run([verify._command_path("git"), "init", "-q", str(root)],
                           check=True, timeout=10)
            original = b'{\r\n  "version": 1,\r\n  "status": "keep"}\r\n'
            report.write_bytes(original)
            with self.assertRaisesRegex(ValueError, "existing non-report"):
                verify.checked_report_path(report, root, root / "config.json")
            self.assertEqual(report.read_bytes(), original)

    def test_report_writer_uses_literal_lf_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.json"
            verify.write_report(report, {"version": 1, "status": "passed"})
            self.assertTrue(report.read_bytes().startswith(b'{\n  "version": 1,\n  "status": "'))

    def test_nan_report_does_not_replace_old_report(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"; path.write_text("old")
            with self.assertRaises(ValueError): verify.write_report(path, {"x": float("nan")})
            self.assertEqual(path.read_text(), "old")
            self.assertEqual(list(path.parent.iterdir()), [path])


class LineCountAdversarialTests(unittest.TestCase):
    SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_loc.py"

    def setUp(self):
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.git("init", "-q")
        (self.root / "a.py").write_text("x = 1\n" * 100)
        self.git("add", ".")
        self.git("-c", "user.name=T", "-c", "user.email=t@example.invalid",
                 "commit", "-q", "-m", "base")

    def git(self, *args):
        return subprocess.run([verify._command_path("git"), *args], cwd=self.root,
                              check=True, capture_output=True, timeout=15)

    def test_gitattributes_cannot_hide_added_code(self):
        (self.root / "bloat.py").write_text("y = 2\n" * 500)
        for attribute in ("-diff", "binary"):
            (self.root / ".gitattributes").write_text("bloat.py " + attribute + "\n")
            with self.subTest(attribute=attribute):
                result = subprocess.run([sys.executable, str(self.SCRIPT), "--base", "HEAD",
                                         "--min-percent", "0"], cwd=self.root,
                                        capture_output=True, timeout=15)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(b"-> 600 now", result.stdout)

    def test_gitattributes_cannot_hide_base_code(self):
        (self.root / ".gitattributes").write_text("*.py -diff\n")
        self.git("add", ".gitattributes")
        self.git("-c", "user.name=T", "-c", "user.email=t@example.invalid",
                 "commit", "-q", "-m", "binary attributes")
        result = subprocess.run([sys.executable, str(self.SCRIPT), "--base", "HEAD",
                                 "--min-percent", "0"], cwd=self.root,
                                capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"code lines 100 at HEAD -> 100 now", result.stdout)

    def test_python_line_endings_count_equally_in_worktree(self):
        lines = [b"", b" \t", b"  # comment", b"x = 1", b"y = 2 # inline"] * 300
        endings = (b"\n", b"\r\n", b"\r")
        sources = [ending.join(lines) for ending in endings]
        sources.append(b"".join(line + endings[index % 3]
                                for index, line in enumerate(lines)))
        for index, source in enumerate(sources):
            compile(source, "a.py", "exec")
            (self.root / "a.py").write_bytes(source)
            result = subprocess.run([sys.executable, str(self.SCRIPT), "--base", "HEAD"],
                                    cwd=self.root, capture_output=True, timeout=15)
            with self.subTest(index=index):
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(b"code lines 100 at HEAD -> 600 now", result.stdout)

    def test_cr_only_base_code_is_counted(self):
        (self.root / "a.py").write_bytes(b"\r".join([b"# comment", b"x = 1", b""] * 100))
        self.git("-c", "core.autocrlf=false", "add", "a.py")
        self.git("-c", "user.name=T", "-c", "user.email=t@example.invalid",
                 "commit", "-q", "-m", "CR-only base")
        (self.root / "a.py").write_bytes(b"x = 1\n" * 600)
        result = subprocess.run([sys.executable, str(self.SCRIPT), "--base", "HEAD"],
                                cwd=self.root, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(b"code lines 100 at HEAD -> 600 now", result.stdout)

    def test_non_utf8_encoding_cookies_cannot_hide_worktree_code(self):
        payloads = {
            "utf-7": b"+AAo-".join([b"x = 1"] * 100),
            "unicode_escape": b"\\n".join([b"x = 1"] * 100),
            "raw_unicode_escape": b"\\u000a".join([b"x = 1"] * 100),
            "cp037": ("x = 1\n" * 100).encode("cp037"),
        }
        for encoding, payload in payloads.items():
            for ending in (b"\n", b"\r\n", b"\r"):
                for prefix in (b"", b"#!/usr/bin/env python" + ending):
                    (self.root / "a.py").write_bytes(
                        prefix + b"# coding: " + encoding.encode() + ending + payload + ending)
                    result = subprocess.run([sys.executable, str(self.SCRIPT), "--base", "HEAD"],
                                            cwd=self.root, capture_output=True, timeout=15)
                    with self.subTest(encoding=encoding, ending=ending, prefix=prefix):
                        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                        self.assertIn(b"a.py", result.stderr)
                        self.assertIn(b"non-UTF-8", result.stderr)

    def test_non_utf8_encoding_cookies_are_rejected_at_base(self):
        (self.root / "a.py").write_bytes(b"# coding: utf-7\n" + b"x = 1+AAo-" * 100)
        self.git("add", "a.py")
        self.git("-c", "user.name=T", "-c", "user.email=t@example.invalid",
                 "commit", "-q", "-m", "encoded base")
        (self.root / "a.py").write_bytes(b"x = 1\n" * 80)
        result = subprocess.run([sys.executable, str(self.SCRIPT), "--base", "HEAD"],
                                cwd=self.root, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn(b"a.py", result.stderr)
        self.assertIn(b"non-UTF-8", result.stderr)

    def test_utf8_encoding_cookies_are_allowed(self):
        for encoding in ("utf-8", "utf8", "UTF-8", "utf_8", "utf-8-sig"):
            for prefix in (b"", b"#!/usr/bin/env python\n"):
                (self.root / "a.py").write_bytes(
                    prefix + b"# coding: " + encoding.encode() + b"\n" + b"x = 1\n" * 80)
                result = subprocess.run([sys.executable, str(self.SCRIPT), "--base", "HEAD"],
                                        cwd=self.root, capture_output=True, timeout=15)
                with self.subTest(encoding=encoding, prefix=prefix):
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_utf8_tokenizer_suffix_cookies_are_allowed(self):
        for encoding in ("utf-8-unix", "utf-8-dos", "UTF_8_UNIX", "utf_8_dos"):
            for prefix in (b"", b"#!/usr/bin/env python\n"):
                source = prefix + b"# coding: " + encoding.encode() + b"\n" + b"x = 1\n" * 80
                compile(source, "a.py", "exec")
                (self.root / "a.py").write_bytes(source)
                result = subprocess.run([sys.executable, str(self.SCRIPT), "--base", "HEAD"],
                                        cwd=self.root, capture_output=True, timeout=15)
                with self.subTest(encoding=encoding, prefix=prefix):
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn(b"code lines 100 at HEAD -> 80 now", result.stdout)

    def test_git_output_settings_cannot_hide_encoding_cookies(self):
        global_config = self.root / "global.gitconfig"
        payload = b"# coding: utf-7\n" + b"x = 1+AAo-" * 600 + b"\n"
        compile(payload, "a.py", "exec")
        with patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(global_config)}):
            for location in ("local", "global"):
                for key, value in (("grep.column", "true"), ("color.ui", "always"),
                                   ("color.grep", "always")):
                    global_config.write_text("", encoding="utf-8")
                    if location == "local":
                        self.git("config", key, value)
                    else:
                        section, option = key.split(".")
                        global_config.write_text(f"[{section}]\n{option} = {value}\n",
                                                 encoding="utf-8")
                    with self.subTest(location=location, setting=key):
                        for source, expected in ((b"x = 1\n" * 80, 0), (payload, 2)):
                            (self.root / "a.py").write_bytes(source)
                            result = subprocess.run([sys.executable, str(self.SCRIPT),
                                                     "--base", "HEAD"], cwd=self.root,
                                                    capture_output=True, timeout=15)
                            self.assertEqual(result.returncode, expected,
                                             result.stdout + result.stderr)
                            if expected == 0:
                                self.assertIn(b"code lines 100 at HEAD -> 80 now", result.stdout)
                            else:
                                self.assertIn(b"non-UTF-8", result.stderr)
                                self.assertIn(b"a.py", result.stderr)
                    if location == "local":
                        self.git("config", "--unset", key)

    def test_unparsed_encoding_headers_are_execution_errors(self):
        valid = b"a.py\0" + b"1\0x = 1\n"
        for output in (b"garbage\n", b"garbage\0" + valid,
                       valid + b"garbage\n", valid + b"garbage\0" + valid):
            result = subprocess.run([sys.executable, "-c", r"""
import runpy, subprocess, sys
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
script, header = sys.argv[2], bytes.fromhex(sys.argv[3])
sys.argv = [script, '--base', 'HEAD', '--min-percent', '0']
outputs = [subprocess.CompletedProcess([], 0, stdout=b'a' * 40 + b'\n'),
           subprocess.CompletedProcess([], 0, stdout=header),
           subprocess.CompletedProcess([], 0, stdout=b'a.py\0' + b'100\n'),
           subprocess.CompletedProcess([], 1, stdout=b''),
           subprocess.CompletedProcess([], 0, stdout=b'a.py\0' + b'1\0x = 1\n'),
           subprocess.CompletedProcess([], 0, stdout=b'a.py\0' + b'100\n'),
           subprocess.CompletedProcess([], 1, stdout=b'')]
with patch('subprocess.run', side_effect=outputs):
    runpy.run_path(script, run_name='__main__')
""", str(self.SCRIPT.parent), str(self.SCRIPT), output.hex()], cwd=self.root,
                                    capture_output=True, timeout=15)
            with self.subTest(output=output):
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn(b"git grep", result.stderr)
                self.assertNotIn(b"Traceback", result.stderr)

    def test_valid_encoding_headers_allow_empty_and_unterminated_files(self):
        for name, source in (("empty.py", b""), ("blank.py", b"\n"),
                             ("comment.py", b"# comment"), ("space name.py", b"x = 1")):
            (self.root / name).write_bytes(source)
        result = subprocess.run([sys.executable, str(self.SCRIPT), "--base", "HEAD",
                                 "--min-percent", "0"], cwd=self.root,
                                capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(b"code lines 100 at HEAD -> 101 now", result.stdout)

    def test_non_utf8_cookie_spellings_cannot_hide_code(self):
        headers = (b"\r# coding: utf-7\r", b"\r\n# coding: utf-7\r\n",
                   b" \n# coding: utf-7\n", b"\f\n# coding: utf-7\n",
                   b" # coding: utf-7\n", b"\t# coding: utf-7\n", b"\f# coding: utf-7\n",
                   b"#coding=utf-7\n", b"# vim: set fileencoding=utf-7 :\n",
                   b"# coding:\tutf-7\n", b"# coding:   utf-7\n",
                   b"# coding: utf-7 coding: utf-8\n")
        for header in headers:
            source = header + b"x = 1+AAo-" * 600 + b"\n"
            compile(source, "a.py", "exec")
            (self.root / "a.py").write_bytes(source)
            result = subprocess.run([sys.executable, str(self.SCRIPT), "--base", "HEAD"],
                                    cwd=self.root, capture_output=True, timeout=15)
            with self.subTest(header=header):
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn(b"non-UTF-8", result.stderr)
                self.assertIn(b"a.py", result.stderr)

    def test_gitattributes_cannot_hide_encoding_cookies(self):
        (self.root / "a.py").write_bytes(b"# coding: utf-7\n" + b"x = 1+AAo-" * 600 + b"\n")
        for attribute in ("binary", "-diff"):
            (self.root / ".gitattributes").write_text("*.py " + attribute + "\n")
            result = subprocess.run([sys.executable, str(self.SCRIPT), "--base", "HEAD"],
                                    cwd=self.root, capture_output=True, timeout=15)
            with self.subTest(attribute=attribute):
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn(b"non-UTF-8", result.stderr)
                self.assertIn(b"a.py", result.stderr)

    def test_formfeed_and_vertical_tab_indentation_count(self):
        for indent in (b"\v", b"\f"):
            for ending in (b"\n", b"\r\n", b"\r"):
                lines = [indent + b"# comment", indent, indent + b"x = 1"] * 600
                (self.root / "a.py").write_bytes(ending.join(lines) + ending)
                result = subprocess.run([sys.executable, str(self.SCRIPT), "--base", "HEAD"],
                                        cwd=self.root, capture_output=True, timeout=15)
                with self.subTest(indent=indent, ending=ending):
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertIn(b"code lines 100 at HEAD -> 600 now", result.stdout)

    def test_encoding_cookies_after_second_line_are_ignored(self):
        for ending in (b"\n", b"\r\n", b"\r"):
            (self.root / "a.py").write_bytes(
                ending * 2 + b"# coding: utf-7" + ending + (b"x = 1" + ending) * 80)
            result = subprocess.run([sys.executable, str(self.SCRIPT), "--base", "HEAD"],
                                    cwd=self.root, capture_output=True, timeout=15)
            with self.subTest(ending=ending):
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mixed_case_python_extensions_count_at_base_and_worktree(self):
        for name in ("BLOAT.PY", "Mixed.Py"):
            (self.root / name).write_text("y = 2\n" * 250)
        (self.root / "tests").mkdir()
        (self.root / "tests" / "EXCLUDED.PY").write_text("z = 3\n" * 500)
        for tracked in (False, True):
            if tracked:
                self.git("add", ".")
                self.git("-c", "user.name=T", "-c", "user.email=t@example.invalid",
                         "commit", "-q", "-m", "mixed case extensions")
            result = subprocess.run([sys.executable, str(self.SCRIPT), "--base", "HEAD",
                                     "--min-percent", "0"], cwd=self.root,
                                    capture_output=True, timeout=15)
            with self.subTest(tracked=tracked):
                self.assertEqual(result.returncode, 0 if tracked else 1, result.stderr)
                expected = b"code lines 600" if tracked else b"code lines 100"
                self.assertIn(expected + b" at HEAD -> 600 now", result.stdout)

    def test_non_utf8_git_output_is_execution_error(self):
        bindir = self.root / "bin"; bindir.mkdir()
        if sys.platform == "win32":
            (bindir / "raw.bin").write_bytes(b"\xff")
            (bindir / "git.cmd").write_text('@type "%~dp0raw.bin"\n')
        else:
            tool = bindir / "git"
            tool.write_text("#!/bin/sh\nprintf '\\377'\n")
            tool.chmod(0o755)
        env = dict(os.environ, PATH=str(bindir), PATHEXT=".CMD")
        result = subprocess.run([sys.executable, str(self.SCRIPT), "--base", "HEAD"],
                                cwd=self.root, env=env, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn(b"Traceback", result.stderr)
        self.assertNotIn(b"Exception in thread", result.stderr)

    def test_missing_git_is_execution_error(self):
        bindir = self.root / "empty-bin"; bindir.mkdir()
        env = dict(os.environ, PATH=str(bindir))
        result = subprocess.run([sys.executable, str(self.SCRIPT), "--base", "HEAD"],
                                cwd=self.root, env=env, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn(b"Traceback", result.stderr)

    def test_extreme_git_count_is_execution_error(self):
        result = subprocess.run([sys.executable, "-c", r"""
import runpy, subprocess, sys
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
script = sys.argv[2]
sys.argv = [script, '--base', 'HEAD']
outputs = [subprocess.CompletedProcess([], 0, stdout=b'a' * 40 + b'\n'),
           subprocess.CompletedProcess([], 1, stdout=b''),
           subprocess.CompletedProcess([], 0, stdout=b'a.py\0' + b'9' * 5000 + b'\n')]
with patch('subprocess.run', side_effect=outputs):
    runpy.run_path(script, run_name='__main__')
""", str(self.SCRIPT.parent), str(self.SCRIPT)], cwd=self.root,
                                capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn(b"debloat gate:", result.stderr)
        self.assertNotIn(b"Traceback", result.stderr)

    def test_git_grep_failure_has_diagnostic(self):
        result = subprocess.run([sys.executable, "-c", r"""
import runpy, subprocess, sys
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
script = sys.argv[2]
sys.argv = [script, '--base', 'HEAD']
outputs = [subprocess.CompletedProcess([], 0, stdout=b'a' * 40 + b'\n'),
           subprocess.CompletedProcess([], 128, stdout=b'')]
with patch('subprocess.run', side_effect=outputs):
    runpy.run_path(script, run_name='__main__')
""", str(self.SCRIPT.parent), str(self.SCRIPT)], cwd=self.root,
                                capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn(b"git grep", result.stderr)
        self.assertIn(b"128", result.stderr)
        self.assertNotIn(b"Traceback", result.stderr)

    @unittest.skipUnless(sys.platform == "win32", "Windows executable lookup")
    def test_check_loc_git_ignores_caller_cwd(self):
        shutil.copyfile(Path(os.environ["SystemRoot"]) / "System32" / "cmd.exe",
                        self.root / "git.exe")
        env = {k: v for k, v in os.environ.items()
               if k.upper() != "NODEFAULTCURRENTDIRECTORYINEXEPATH"}
        result = subprocess.run([sys.executable, str(self.SCRIPT), "--base", "HEAD",
                                 "--min-percent", "0"], cwd=self.root, env=env,
                                input=b"echo hijacked>planted-git-ran\r\nexit 0\r\n",
                                capture_output=True, timeout=15)
        self.assertFalse((self.root / "planted-git-ran").exists(), "the planted git.exe ran")
        self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipUnless(sys.platform == "win32", "Windows path and process semantics")
class WindowsAdversarialTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="verify attacks ")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_report_namespace_cannot_write_git_hook(self):
        subprocess.run([verify._command_path("git"), "init", "-q", str(self.root)], check=True, timeout=10)
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
        subprocess.run([verify._command_path("git"), "init", "-q", str(self.root)], check=True, timeout=10)
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
        subprocess.run([verify._command_path("git"), "init", "-q", str(self.root)], check=True, timeout=10)
        source = self.root / "source.txt"; source.write_text("keep")
        for target in [str(source) + ".", str(source) + " ", str(source) + "::$DATA",
                       "\\\\?\\" + str(source), "\\\\.\\" + str(source)]:
            with self.subTest(target=target), self.assertRaises(ValueError):
                verify.checked_report_path(target, self.root, self.root / "config.json")
        self.assertEqual(source.read_text(), "keep")

    def test_short_git_alias_is_protected(self):
        import ctypes
        subprocess.run([verify._command_path("git"), "init", "-q", str(self.root)], check=True, timeout=10)
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
        with patch.dict(os.environ, {"PATH": str(bindir)}):
            os.environ.pop("NoDefaultCurrentDirectoryInExePath", None)
            try:
                os.chdir(caller)
                report = verify.run_gates(value, self.root)
            finally:
                os.chdir(previous)
        self.assertFalse(marker.exists(), "CreateProcess fell back to the caller's executable")
        self.assertEqual(report["gates"][0]["status"], "launch_error")
        self.assertEqual(report["gates"][1]["status"], "not_run")

    def test_relative_executable_uses_repository_root(self):
        caller = self.root / "caller"; (caller / "bin").mkdir(parents=True)
        (self.root / "bin").mkdir()
        system = Path(os.environ["SystemRoot"]) / "System32"
        shutil.copyfile(system / "where.exe", self.root / "bin" / "tool.exe")
        shutil.copyfile(system / "cmd.exe", caller / "bin" / "tool.exe")
        previous = Path.cwd()
        for setting in (None, "1"):
            marker = self.root / f"hijacked-{setting}"
            value = config()
            value["gates"][0]["argv"] = [os.path.join("bin", "tool.exe"), "/c",
                                         f"echo hijacked>{marker.name}"]
            with self.subTest(setting=setting), patch.dict(os.environ):
                os.environ.pop("NoDefaultCurrentDirectoryInExePath", None)
                if setting is not None:
                    os.environ["NoDefaultCurrentDirectoryInExePath"] = setting
                try:
                    os.chdir(caller)
                    report = verify.run_gates(value, self.root)
                finally:
                    os.chdir(previous)
                self.assertFalse(marker.exists(), "the caller's relative executable ran")
                self.assertEqual(report["gates"][0]["status"], "failed")
                self.assertEqual(report["gates"][1]["status"], "not_run")

    def test_git_metadata_query_ignores_caller_cwd(self):
        subprocess.run([verify._command_path("git"), "init", "-q", str(self.root)], check=True, timeout=10)
        caller = self.root / "caller"; caller.mkdir()
        shutil.copyfile(Path(os.environ["SystemRoot"]) / "System32" / "where.exe",
                        caller / "git.exe")
        previous = Path.cwd()
        with patch.dict(os.environ):
            os.environ.pop("NoDefaultCurrentDirectoryInExePath", None)
            try:
                os.chdir(caller)
                target = verify.checked_report_path(self.root / "report.json", self.root,
                                                    self.root / "config.json")
            finally:
                os.chdir(previous)
        self.assertEqual(target, self.root / "report.json")

    def test_adversarial_git_ignores_caller_cwd(self):
        shutil.copyfile(Path(os.environ["SystemRoot"]) / "System32" / "where.exe",
                        self.root / "git.exe")
        env = {k: v for k, v in os.environ.items()
               if k.upper() != "NODEFAULTCURRENTDIRECTORYINEXEPATH"}
        result = subprocess.run([sys.executable, "-c",
            "import sys, unittest; sys.path.insert(0, sys.argv.pop(1)); unittest.main(module=None)",
            str(Path(__file__).resolve().parents[1]),
            "tests.test_adversarial.AdversarialTests.test_git_metadata_is_protected"],
            cwd=self.root, env=env, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

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

    def test_unsupported_batch_paths_are_rejected_before_launch(self):
        for extension in (".cmd", ".BAT"):
            tool = self.root / ("tool" + extension); tool.write_text("@exit /b 0\n")
            commands = [str(tool) + suffix for suffix in (".", ". .")]
            commands.append("\\\\?\\" + str(tool))
            for command in commands:
                value = config(); value["gates"][0]["argv"] = [command]
                with self.subTest(command=command), patch.object(
                        verify.subprocess, "run", wraps=subprocess.run) as run:
                    report = verify.run_gates(value, self.root)
                    self.assertEqual(report["gates"][0]["status"], "launch_error")
                    self.assertIsNone(report["gates"][0]["exit_code"])
                    self.assertEqual(report["gates"][1]["status"], "not_run")
                    run.assert_not_called()

    def test_batch_executable_path_cannot_expand_environment_variables(self):
        tool = self.root / "tool%VERIFY_INJECTION%.cmd"; tool.write_text("@exit /b 0\n")
        marker = self.root / "injected"
        (self.root / "tool-expanded.cmd").write_text(f"@echo injected>{marker.name}\n")
        value = config(); value["gates"][0]["argv"] = [str(tool)]
        with patch.dict(os.environ, {"VERIFY_INJECTION": "-expanded"}):
            report = verify.run_gates(value, self.root)
        self.assertFalse(marker.exists(), "cmd.exe expanded the executable's file name")
        self.assertEqual(report["gates"][0]["status"], "launch_error")

    def test_batch_path_delimiters_cannot_select_a_sibling(self):
        directory = tempfile.TemporaryDirectory(prefix="verify-delimiters-")
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.assertFalse(any(char.isspace() for char in str(root)), str(root))
        (root / "tool.bat").write_text("@exit /b 9\n")
        delimiters = ",;=" + "".join(chr(n) for n in range(32, sys.maxunicode + 1)
                                      if chr(n).isspace())
        previous = Path.cwd()
        try:
            os.chdir(root)
            for extension in (".cmd", ".bat"):
                for delimiter in delimiters:
                    tool = root / ("tool" + delimiter + "lint" + extension)
                    tool.write_text("@exit /b 0\n")
                    for args in ([], ["hello world"]):
                        value = config()
                        value["gates"][0]["argv"] = [os.path.join(".", tool.name), *args]
                        with self.subTest(extension=extension, delimiter=repr(delimiter), args=args):
                            report = verify.run_gates(value, root)
                            self.assertEqual(report["status"], "passed")
        finally:
            os.chdir(previous)

    def test_safe_batch_arguments_and_paths_with_spaces_still_work(self):
        for extension in (".cmd", ".bat"):
            tool = self.root / ("tool" + extension)
            tool.write_text('@if not "%~1" == "hello world" exit /b 7\n@exit /b 0\n')
            for command in (str(tool), tool.name, tool.stem):
                value = config(); value["gates"][0]["argv"] = [command, "hello world"]
                with self.subTest(command=command), patch.dict(os.environ,
                        {"PATH": str(self.root)}):
                    os.environ.pop("NoDefaultCurrentDirectoryInExePath", None)
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
