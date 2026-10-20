"""Run trusted local verification commands; not a sandbox or merge approval."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import math

GATE_NAMES = ("deterministic", "critic", "debloat")
CONFIG_KEYS = frozenset({"version", "gates"})
GATE_KEYS = frozenset({"name", "argv", "timeout_seconds"})
MAX_TIMEOUT_SECONDS = 3600
REPORT_PREFIX = b'{\n  "version": 1,\n  "status": "'  # how write_report() starts a run_gates() report


def _check_object(obj, expected_keys, where):
    if not isinstance(obj, dict):
        raise ValueError(f"{where} must be a JSON object")
    unknown = sorted(set(obj) - expected_keys, key=str)
    if unknown:
        raise ValueError(f"{where} has unknown keys {unknown}")
    missing = sorted(expected_keys - set(obj))
    if missing:
        raise ValueError(f"{where} is missing keys {missing}")


def validate_config(data):
    """Validate already-parsed config data; return it unchanged or raise ValueError."""
    _check_object(data, CONFIG_KEYS, "config")
    # type() rather than isinstance(): bool is an int subclass and must be rejected.
    version = data["version"]
    if type(version) is not int or version != 1:
        raise ValueError(f"config.version must be the integer 1, got {version!r}")

    gates = data["gates"]
    if not isinstance(gates, list) or len(gates) != len(GATE_NAMES):
        raise ValueError(f"config.gates must be a list of {len(GATE_NAMES)} gates")

    for index, expected_name in enumerate(GATE_NAMES):
        gate = gates[index]
        where = f"gates[{index}]"
        _check_object(gate, GATE_KEYS, where)

        name = gate["name"]
        if name != expected_name:
            raise ValueError(f"{where}.name must be {expected_name!r}, got {name!r}")

        argv = gate["argv"]
        if not isinstance(argv, list) or not argv:
            raise ValueError(f"{where}.argv must be a nonempty list")
        for arg_index, arg in enumerate(argv):
            if (not isinstance(arg, str) or not arg or "\0" in arg
                    or any(0xD800 <= ord(char) <= 0xDFFF for char in arg)):
                raise ValueError(
                    f"{where}.argv[{arg_index}] must be a nonempty Unicode scalar string without NUL"
                )

        timeout = gate["timeout_seconds"]
        field = f"{where}.timeout_seconds"
        if type(timeout) not in (int, float):
            raise ValueError(f"{field} must be a number, got {timeout!r}")
        # Only floats can be NaN/inf; math.isfinite() overflows on huge ints.
        if type(timeout) is float and not math.isfinite(timeout):
            raise ValueError(f"{field} must be finite, got {timeout!r}")
        if not 0 < timeout <= MAX_TIMEOUT_SECONDS:
            raise ValueError(
                f"{field} must be > 0 and <= {MAX_TIMEOUT_SECONDS}, got {timeout!r}"
            )
    return data


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_config(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError("config exceeds 64 KiB")
    try:
        data = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique_object)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("config must be UTF-8 JSON with bounded nesting") from exc
    return validate_config(data)


def _command_path(command):
    if os.path.dirname(command):
        return command
    suffixes = [""]
    if sys.platform == "win32":
        suffixes = [ext for ext in (os.environ.get("PATHEXT") or ".COM;.EXE;.BAT;.CMD")
                    .split(os.pathsep) if ext]
        if command.casefold().endswith(tuple(ext.casefold() for ext in suffixes)):
            suffixes.insert(0, "")
    for directory in os.get_exec_path():
        # Never let Windows add the caller's working directory to executable lookup.
        if sys.platform == "win32" and not os.path.isabs(directory):
            continue
        for suffix in suffixes:
            candidate = Path(directory) / (command + suffix)
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate.absolute())
    raise FileNotFoundError(f"command not found on PATH: {command}")


def run_gates(config, root):
    validate_config(config)
    results = []
    blocked = False
    for gate in config["gates"]:
        result = {"name": gate["name"], "status": "not_run", "exit_code": None}
        if not blocked:
            argv = [sys.executable if arg == "{python}" else arg for arg in gate["argv"]]
            try:
                if os.path.dirname(argv[0]):
                    argv[0] = str((Path(root) / argv[0]).absolute())
                else:
                    argv[0] = _command_path(argv[0])
                # Windows implicitly runs batch files through cmd.exe even with shell=False.
                if (sys.platform == "win32"
                        and Path(argv[0].rstrip(" .")).suffix.casefold() in (".cmd", ".bat")):
                    if argv[0].rstrip(" ").endswith(".") or argv[0].startswith("\\\\?\\"):
                        raise OSError("unsupported Windows batch path")
                    if any(char in '&|<>^()%!"' or ord(char) < 32
                           for arg in argv for char in arg):
                        raise OSError("unsafe Windows batch command or argument")
                    # cmd.exe also splits unquoted paths on punctuation and Unicode whitespace.
                    argv = f'"{argv[0]}" {subprocess.list2cmdline(argv[1:])}'
                completed = subprocess.run(argv, cwd=root, timeout=gate["timeout_seconds"], shell=False)
                result["exit_code"] = completed.returncode
                result["status"] = "passed" if completed.returncode == 0 else "failed"
            except subprocess.TimeoutExpired:
                result["status"] = "timed_out"
            except OSError:
                result["status"] = "launch_error"
            blocked = result["status"] != "passed"
        results.append(result)
    return {"version": 1, "status": "failed" if blocked else "passed",
            "human_approval": "pending", "gates": results}


def _is_within(path, parent):
    # Case-insensitive: default macOS/Windows file systems treat .GIT as .git.
    path, parent = (type(p)(str(p).casefold()) for p in (path, parent))
    return path.is_relative_to(parent)


def checked_report_path(path, root, config_path):
    """Protect config, Git metadata and existing non-report files; not race-proof."""
    path = Path(path).absolute()
    if (sys.platform == "win32" and (path.drive.startswith("\\")
            or any(":" in part or (part not in (".", "..") and part.endswith((".", " ")))
                   for part in path.parts[1:]))):
        raise ValueError("report must use a local Windows path without streams or trailing dots/spaces")
    if path.is_symlink():
        raise ValueError("report target must not be a symlink")
    resolved = path.resolve()
    if resolved == Path(config_path).resolve():
        raise ValueError("report must not overwrite its config")
    protected = [Path(root) / ".git"]
    for option in ("--git-dir", "--git-common-dir"):
        metadata = subprocess.run([_command_path("git"), "rev-parse", option], cwd=root, check=True,
                                  stdout=subprocess.PIPE, timeout=10)
        protected.append(Path(root) / os.fsdecode(metadata.stdout.removesuffix(b"\n")))
    if any(_is_within(resolved, item.resolve()) for item in protected):
        raise ValueError("report must not overwrite Git metadata")
    if path.exists():
        # Only a previous report may be replaced; read just enough to recognize one.
        with path.open("rb") as stream:
            if stream.read(len(REPORT_PREFIX)) != REPORT_PREFIX:
                raise ValueError("report must not overwrite an existing non-report file")
    return path


def write_report(path, report):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent,
                                         prefix=".verification-", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="verification.json")
    parser.add_argument("--report", default=".artifacts/verification.json")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    try:
        config_path = root / args.config
        config = load_config(config_path)
        report_path = checked_report_path(root / args.report, root, config_path)
        report = run_gates(config, root)
        # Recheck after trusted commands may have changed repository paths.
        checked_report_path(report_path, root, config_path)
        write_report(report_path, report)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"verification error: {exc}", file=sys.stderr)
        return 2
    print(f"Verification {report['status']}; human approval pending. Report: {report_path}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
