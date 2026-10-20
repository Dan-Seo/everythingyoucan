import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "verify.py"
spec = importlib.util.spec_from_file_location("verify", MODULE)
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


def config():
    return {"version": 1, "gates": [
        {"name": name, "argv": ["{python}", "-c", "pass"], "timeout_seconds": 5}
        for name in verify.GATE_NAMES]}


class SchemaTests(unittest.TestCase):
    def test_valid_identity_and_no_mutation(self):
        value = config()
        before = copy.deepcopy(value)
        self.assertIs(verify.validate_config(value), value)
        self.assertEqual(value, before)

    def test_schema_failures(self):
        cases = [None, [], {}, {"version": 1, "gates": []}]
        for key, value in [("version", True), ("version", 1.0), ("version", 2),
                           ("gates", {}), ("extra", "unknown")]:
            bad = config(); bad[key] = value; cases.append(bad)
        bad = config(); bad["gates"].reverse(); cases.append(bad)
        for bad in cases:
            with self.subTest(value=bad), self.assertRaises(ValueError):
                verify.validate_config(bad)

    def test_gate_failures(self):
        for key, value in [("name", None), ("argv", []), ("argv", "echo"),
                           ("argv", [""]), ("argv", [3]), ("argv", ["x\0y"]),
                           ("timeout_seconds", True), ("timeout_seconds", 0),
                           ("timeout_seconds", -1), ("timeout_seconds", 3601),
                           ("timeout_seconds", "1"), ("extra", 0)]:
            bad = config(); bad["gates"][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                verify.validate_config(bad)
        for bad_gate in [None, [], {"name": "deterministic"}]:
            bad = config(); bad["gates"][0] = bad_gate
            with self.assertRaises(ValueError): verify.validate_config(bad)

    def test_load_config(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(config()), encoding="utf-8")
            self.assertEqual(verify.load_config(path), config())
            for value in [b"{", b"\xff", b" " * 65537,
                          b'{"version":1,"version":1,"gates":[]}']:
                path.write_bytes(value)
                with self.assertRaises(ValueError): verify.load_config(path)

    def test_load_config_accepts_utf8_bom(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_bytes(b"\xef\xbb\xbf" + json.dumps(config()).encode())
            self.assertEqual(verify.load_config(path), config())


class RunnerTests(unittest.TestCase):
    def test_success(self):
        with tempfile.TemporaryDirectory() as directory:
            report = verify.run_gates(config(), directory)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["human_approval"], "pending")
        self.assertEqual([g["exit_code"] for g in report["gates"]], [0, 0, 0])

    def test_fail_fast_at_every_gate(self):
        for index in range(3):
            value = config()
            value["gates"][index]["argv"] = ["{python}", "-c", "raise SystemExit(7)"]
            with tempfile.TemporaryDirectory() as directory:
                report = verify.run_gates(value, directory)
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["human_approval"], "pending")
            self.assertEqual(report["gates"][index]["exit_code"], 7)
            self.assertEqual([x["status"] for x in report["gates"]],
                             ["passed"] * index + ["failed"] + ["not_run"] * (2-index))

    def test_timeout(self):
        value = config()
        value["gates"][0].update(argv=["{python}", "-c", "import time; time.sleep(10)"],
                                  timeout_seconds=0.05)
        with tempfile.TemporaryDirectory() as directory:
            report = verify.run_gates(value, directory)
        self.assertEqual(report["gates"][0]["status"], "timed_out")
        self.assertIsNone(report["gates"][0]["exit_code"])
        self.assertEqual(report["gates"][1]["status"], "not_run")

    def test_missing_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            value = config(); value["gates"][0]["argv"] = [str(Path(directory)/"absent")]
            report = verify.run_gates(value, directory)
        self.assertEqual(report["gates"][0]["status"], "launch_error")

    def test_command_found_on_path_by_name(self):
        # Windows installs tools such as npm as .cmd files that CreateProcess cannot find by name.
        with tempfile.TemporaryDirectory() as directory:
            windows = sys.platform == "win32"
            tool = Path(directory) / ("tool.cmd" if windows else "tool")
            tool.write_text("@exit /b 0\n" if windows else "#!/bin/sh\nexit 0\n")
            tool.chmod(0o755)
            value = config(); value["gates"][0]["argv"] = ["tool"]
            with patch.dict(verify.os.environ, {"PATH": directory}):
                report = verify.run_gates(value, directory)
        self.assertEqual(report["gates"][0]["status"], "passed")

    def test_report_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "report.json"
            verify.write_report(path, {"human_approval": "pending"})
            self.assertEqual(json.loads(path.read_text()), {"human_approval": "pending"})
            self.assertEqual(list(path.parent.iterdir()), [path])

    def test_atomic_failure_preserves_previous_report(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"; path.write_text("old")
            with patch.object(verify.os, "replace", side_effect=OSError("full")):
                with self.assertRaises(OSError): verify.write_report(path, {})
            self.assertEqual(path.read_text(), "old")
            self.assertEqual(list(path.parent.iterdir()), [path])

    def test_cli_exit_codes_and_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); cfg = root / "config.json"; out = root / "report.json"
            for failure, expected in [(False, 0), (True, 1)]:
                value = config()
                if failure:
                    value["gates"][0]["argv"] = ["{python}", "-c", "raise SystemExit(3)"]
                cfg.write_text(json.dumps(value), encoding="utf-8")
                result = subprocess.run([sys.executable, str(MODULE), "--config", str(cfg),
                                         "--report", str(out)], capture_output=True, timeout=15)
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertEqual(json.loads(out.read_text())["human_approval"], "pending")
            cfg.write_text("{}", encoding="utf-8")
            result = subprocess.run([sys.executable, str(MODULE), "--config", str(cfg),
                                     "--report", str(out)], capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 2)
            self.assertIn(b"verification error", result.stderr)

    def test_output_protections(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); cfg = root / "config.json"; tracked = root / "source.py"
            with self.assertRaises(ValueError): verify.checked_report_path(cfg, root, cfg)
            tracked.write_text("source")
            with patch.object(verify.subprocess, "run", side_effect=[
                    subprocess.CompletedProcess([], 0, stdout=b".git\n")] * 4):
                with self.assertRaises(ValueError): verify.checked_report_path(tracked, root, cfg)
                self.assertEqual(verify.checked_report_path(root/"report.json", root, cfg),
                                 root/"report.json")

    def test_adversarial_module_imports_from_repository_root(self):
        result = subprocess.run([sys.executable, "-c", "import tests.test_adversarial"],
                                cwd=MODULE.parents[1], capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)


class LineCountGateTests(unittest.TestCase):
    SCRIPT = MODULE.parent / "check_loc.py"

    def setUp(self):
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.git("init", "-q")
        (self.root / "scripts").mkdir(); (self.root / "tests").mkdir()
        self.write(10)
        (self.root / "tests" / "test_x.py").write_text("x = 1\n" * 50)
        self.git("add", "."); self.git("-c", "user.name=T", "-c", "user.email=t@example.invalid",
                                      "commit", "-q", "-m", "base")

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True, timeout=15)

    def write(self, code_lines):
        (self.root / "scripts" / "a.py").write_text(
            "# comment\n\n    # indented comment\n" + "x = 1\n" * code_lines)

    def run_gate(self, *args):
        return subprocess.run([sys.executable, str(self.SCRIPT), *args], cwd=self.root,
                              capture_output=True, timeout=15).returncode

    def test_requires_default_twenty_percent_reduction_of_code_lines(self):
        self.write(9)
        self.assertEqual(self.run_gate("--base", "HEAD"), 1)
        self.write(8)
        self.assertEqual(self.run_gate("--base", "HEAD"), 0)

    def test_zero_percent_allows_no_growth_or_reduction_but_rejects_growth(self):
        for lines, expected in [(10, 0), (9, 0), (11, 1)]:
            with self.subTest(lines=lines):
                self.write(lines)
                self.assertEqual(self.run_gate("--base", "HEAD", "--min-percent", "0"),
                                 expected)

    def test_blank_comment_and_test_lines_do_not_count(self):
        self.write(8)
        (self.root / "scripts" / "a.py").write_text(
            (self.root / "scripts" / "a.py").read_text() + "\n# more\n" * 30)
        (self.root / "tests" / "test_x.py").write_text("x = 1\n" * 500)
        self.assertEqual(self.run_gate("--base", "HEAD"), 0)

    def test_paths_and_minimum_are_configurable(self):
        self.write(9)
        self.assertEqual(self.run_gate("--base", "HEAD", "--min-percent", "10"), 0)
        (self.root / "tests" / "test_x.py").write_text("x = 1\n" * 10)
        self.assertEqual(self.run_gate("--base", "HEAD", "tests/"), 0)
        self.assertEqual(self.run_gate("--base", "HEAD", "--min-percent", "101"), 2)

    def test_missing_or_invalid_base_fails(self):
        self.write(1)
        for args in [(), ("--base", ""), ("--base", "no-such-ref"), ("--base", "--help")]:
            with self.subTest(args=args):
                self.assertEqual(self.run_gate(*args), 2)


if __name__ == "__main__":
    unittest.main()
