"""Debloat gate: fail unless code lines shrank by --min-percent since --base."""
import argparse
import re
import subprocess
import sys

from verify import _command_path

# ponytail: only '#' comments are recognized; add other comment syntaxes when non-Python files are counted.
CODE_LINE = r"^[[:space:]]*[^[:space:]#]"


def count_code_lines(*grep_args):
    # With -z -c, git grep prints "<file>\0<count>\n"; exit 1 only means nothing matched.
    result = subprocess.run([_command_path("git"), "grep", "-a", "-z", "-c", "-E", "-e", CODE_LINE, *grep_args],
                            stdout=subprocess.PIPE, timeout=60)
    if result.returncode not in (0, 1):
        raise SystemExit(2)
    return sum(int(n) for n in re.findall(rb"\0(\d+)\n", result.stdout))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="commit before the debloating pass")
    parser.add_argument("--min-percent", type=int, default=20)
    parser.add_argument("pathspecs", nargs="*", default=["*.py", ":(exclude)tests/"])
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
    except (OSError, UnicodeError, subprocess.SubprocessError) as exc:
        print(f"debloat gate: {exc}", file=sys.stderr)
        raise SystemExit(2)
