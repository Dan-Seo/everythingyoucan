# everythingyoucan

A dependency-free Python starter for the design → implement → verify → human
review workflow described in the original `CLAUDE.md`. This is a template, not an
application, a sandbox, a security certification or an autonomous merge system.

## Quick start

Requires Python 3.10+ and Git. No package installation is needed. Run inside a
Git working tree: report protection queries Git metadata.

For the source ZIP, extract it into a new directory and initialize Git before
using report protection:

```sh
git init
```

The debloat gate additionally requires a baseline commit containing code;
`git init` alone is not enough. Existing non-report files are protected whether
tracked, ignored or untracked.

Alternatively, overlay the source onto a clone of this repository. The accompanying
patch adds the starter files and extends .gitignore while preserving its existing
exclusion. Apply it with `git apply` to the
original clean checkout. Do not apply both the ZIP overlay and the patch.

```sh
python3 -m unittest discover -s tests -v
python3 scripts/verify.py --config verification.json
```

Earlier evidence covers Linux/Python 3.12.14. The review-fix stage also runs the
tests on Windows; macOS has not been tested. The newline-parent worktree
regression is skipped on Windows because Windows filenames cannot contain
newlines; Windows-specific path and process regressions run there instead.

On Windows use `python` instead of `python3`. Commands in the configuration use
`{python}` to select the interpreter running the harness. Paths are resolved
relative to the repository, so invoking the script from another directory works.

The runner stops after the first failed gate. Exit codes are 0 for all commands
passing, 1 for a gate failure, and 2 for invalid configuration/report I/O. Output
is streamed to the terminal. The JSON report defaults to
`.artifacts/verification.json`; use `--report path.json` for a different path.
Reports now use LF line endings, and existing prefixes are compared as bytes.
Old CRLF reports are not overwritten: select a new report path or manually
move/remove the old file before running again.
A report always says `human_approval: pending`, even when every command passes.
Existing reports can be stale after an interrupted or invalid run. Check the
current process exit and actual output, not merely the presence of a report.

## What's here

- `spec.md`: implementation scope, exact schema and acceptance criteria.
- `specs/TEMPLATE_spec.md`: copy for a new task before editing code.
- `scripts/verify.py`: strict JSON loading, ordered trusted command execution,
  finite per-command timeout, fail-fast behavior and atomic report replacement.
- `verification.json`: deterministic tests, adversarial regressions and a code
  line count check (`scripts/check_loc.py`) against a base commit. The third
  command measures lines only; it does not replace the simplification review
  recorded in `docs/REVIEW.md`.
- `docs/roles.md`: inactive role templates, not installed Claude agents.
- `tests/`: standard-library unit and adversarial tests.

## Debloat baseline

This repository starts with `--min-percent 0`, which rejects code growth and
allows unchanged or reduced code. No debloating pass has happened yet: safety
fixes increased the measured count from 161 to 215 code lines in the first
review-fix commit and grew further in the second, so a 20% reduction
requirement is premature. `check_loc.py` still defaults to 20% as required by
CLAUDE.md Gate 3. When a real debloating pass starts, set this repository's
minimum to 20% and compare against the commit before that pass.

The baseline is repinned to the PM's second review-fix commit
`912dd6af7e4a298a356eab47c65fe243244e88c8`, with `--min-percent 0`.
This follows the owner's decision to prohibit growth relative to the fix commit,
including the safety fixes in the baseline rather than claiming they reduced code.
All three gates must pass for unchanged code. `docs/RESULTS.md` records the
actual stage 3 executions after repinning this baseline.
The counter uses `git grep -a` so `.gitattributes` binary/`-diff` flags cannot
hide matching files; non-ignored untracked Python files also count.
Git execution, timeout and output-decoding errors exit with code 2.

## Trust boundaries

Review every config before running it. Its argv arrays are executable
instructions with your account's permissions. `shell=False` prevents incidental
shell parsing; it does not make a command safe. No command denylist, sandbox,
credential protection or network isolation is implemented by this runner.

Timeout handling terminates and reaps the direct child. It does NOT guarantee
portable cleanup of descendant processes. Do not use untrusted, daemonizing or
background-process commands. Concurrent runs should use different report paths.
Atomic replacement avoids partial JSON, but the last writer wins for a shared
path. Reports are unsigned local evidence, not tamper-proof attestations.

The runner rejects report targets that would overwrite the config, Git metadata
(including linked-worktree metadata, compared case-insensitively), or any
existing non-report file. Only the exact LF report prefix, compared in binary
mode, identifies a previous report; another tool's JSON with the same prefix is
indistinguishable. This is not an authenticity check. Symlink targets are rejected. Windows
also rejects namespace prefixes (`\\?\`, `\\.\`), UNC paths, NTFS alternate
data streams, and path components ending in dots or spaces. Paths are checked
again after commands execute, but files can still change between checking and
writing; this is not protection against a hostile filesystem race.

Windows executable lookup, including Git calls in `verify.py`, `check_loc.py`
and the tests, searches only absolute
PATH entries and PATHEXT candidates without implicitly searching the current
directory. Windows can still launch batch files through cmd.exe with
`shell=False`, so the runner rejects unsafe batch paths and arguments. It always
double-quotes the resolved batch path, including paths without spaces, to prevent
splitting on delimiters such as `,`, `;`, `=` and U+00A0.
Hijacking tests remove `NoDefaultCurrentDirectoryInExePath` from the environment
used for the attack so an OS lookup restriction cannot mask a regression.
Stage 3 records both unittest commands with the variable set to `1` and removed.

The original `.claude/settings.json` refers to a machine-specific Windows hook.
It has been deliberately preserved, not repaired, disabled or replaced. This
starter does not make that hook portable. Configure an approved hook separately
before using Claude tools inside the repository. Do not bypass a failing guard.

## Work on a new task

1. Copy the task spec, record assumptions and define concrete acceptance tests.
2. Split work into small isolated changes. Review dependencies before installing.
3. Replace gate argv commands with the task's real checks. Run all tests after
   fixes and simplification; preserve concrete adversarial regression cases.
   On Windows, `.cmd`/`.bat` paths or arguments containing `& | < > ^ ( ) % ! "` or control characters below U+0020 produce `launch_error`; batch commands requiring these characters are intentionally unsupported.
4. Inspect source, test output and limitations. Ask the human architect for merge
   approval separately. No script here pushes, merges, deploys or calls a model.

See `docs/REVIEW.md` for implementation provenance, measured checks and residual
limits. Passing tests do not mean defect-free software.
