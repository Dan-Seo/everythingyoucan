"""Debloat gate: fail unless code lines shrank by --min-percent since --base."""
import argparse
import codecs
import re
import subprocess
import sys

from verify import _command_path

# ponytail: only '#' comments are recognized; add other comment syntaxes when non-Python files are counted.
CODE_LINE = "[ \t\v\f]*[^[:space:]#]"


def count_code_lines(*grep_args):
    count = 0
    # -c counts LF lines; -o emits each CR-led code match on a separate output line.
    for prefix, options in (("", ("-z", "-n", "-m", "2")),
                            ("^", ("-z", "-c")),
                            ("\r", ("-h", "-o", "--no-break", "--no-heading"))):
        result = subprocess.run([_command_path("git"), "grep", "-a", *options,
                                 "--no-color", "--no-column", "-E", "-e",
                                 prefix + CODE_LINE if prefix else "^", *grep_args],
                                stdout=subprocess.PIPE, timeout=60)
        if result.returncode not in (0, 1):
            raise OSError(f"git grep failed with exit code {result.returncode}")
        if not prefix:
            headers = {}
            records = re.compile(rb"([^\0]+)\0[12]\0([^\n]*)\n")
            if records.sub(b"", result.stdout):
                raise ValueError("unexpected git grep header output")
            for path, line in records.findall(result.stdout):
                headers[path] = headers.get(path, b"") + line + b"\n"
            for path, header in headers.items():
                for line in re.split(rb"\r\n?|\n", header.removeprefix(codecs.BOM_UTF8))[:2]:
                    if not re.match(rb"[ \t\f]*(?:#|$)", line):
                        break
                    cookie = re.match(rb"[ \t\f]*#.*?coding[:=][ \t]*([-\w.]+)", line)
                    if cookie:
                        try:
                            name = cookie[1].decode("ascii")
                            encoding = ("utf-8" if name.lower().replace("_", "-").startswith("utf-8-")
                                        else codecs.lookup(name).name)
                        except LookupError:
                            encoding = None
                        if encoding not in ("utf-8", "utf-8-sig"):
                            raise ValueError("non-UTF-8 encoding declaration in "
                                             + path.decode("utf-8", "replace"))
        else:
            count += (sum(int(n) for n in re.findall(rb"\0(\d+)\n", result.stdout))
                      if prefix == "^" else result.stdout.count(b"\n"))
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="commit before the debloating pass")
    parser.add_argument("--min-percent", type=int, default=20)
    parser.add_argument("pathspecs", nargs="*", default=[":(icase)*.py", ":(exclude)tests/"])
    args = parser.parse_args()
    if not 0 <= args.min_percent <= 100:
        parser.error("--min-percent must be between 0 and 100")
    base = subprocess.run([_command_path("git"), "rev-parse", "--verify", "--quiet", "--end-of-options",
                           args.base + "^{commit}"], stdout=subprocess.PIPE, timeout=10)
    if base.returncode != 0:
        print(f"debloat gate: base ref {args.base!r} is not a commit", file=sys.stderr)
        return 2
    before = count_code_lines(base.stdout.strip().decode("ascii"), "--", *args.pathspecs)
    after = count_code_lines("--untracked", "--", *args.pathspecs)
    if before == 0:
        print("debloat gate: no code lines at the base ref; check the pathspecs", file=sys.stderr)
        return 2
    print(f"code lines {before} at {args.base} -> {after} now; "
          f"reduction {(before - after) * 100 / before:.1f}% (required {args.min_percent}%)")
    return 0 if (before - after) * 100 >= before * args.min_percent else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"debloat gate: {exc}", file=sys.stderr)
        raise SystemExit(2)
