# everythingyoucan

**Ship AI-written Python through a verification funnel, not vibes.**

- **What:** a dependency-free Python starter for the design → implement → verify → human-review workflow in [`CLAUDE.md`](CLAUDE.md).
- **Who:** developers using Claude Code (or any coding agent) who want executable gates before they trust generated code.
- **How:** copy the spec template, implement, then run the 3-gate harness — deterministic tests, adversarial regressions, LOC check — and ask a human for merge approval.

```sh
python3 -m unittest discover -s tests && python3 scripts/verify.py --config verification.json
```

83 committed tests, zero third-party dependencies — `python3 -m unittest discover -s tests` reports `Ran 83 tests ... OK` with stdlib only. This is a template, not an application, a sandbox, a security certification or an autonomous merge system.

## Why this exists

Coding agents generate code fast; the bottleneck is trusting it. `CLAUDE.md` prompt templates tell the agent *what to do*, but markdown alone cannot stop a bad merge. This starter adds the missing half: an executable funnel (`scripts/verify.py` + `verification.json`) that runs deterministic tests, adversarial regression tests, and a code-size check in order, fails fast, and always leaves `human_approval: pending` for a person to resolve. Every gate exit code and limitation is documented in [`docs/REVIEW.md`](docs/REVIEW.md) and [`docs/RESULTS.md`](docs/RESULTS.md).

## When to use (and when not to)

Use it when you want a spec-first, agent-assisted Python workflow with no toolchain to install — Python 3.10+ and Git are the only prerequisites. It fits small libraries, scripts, and exercises where hostile inputs and silent regressions matter.

Do not use it as a sandbox, a security certification, or an auto-merge bot: configured commands run with your account's permissions, reports are unsigned local evidence, and no script here pushes, merges, deploys, or calls a model. See [Trust boundaries](#trust-boundaries).

## How it compares

- [CLAUDE.md template collections](https://github.com/abhishekray07/claude-md-templates) and [production CLAUDE.md templates](https://github.com/seankim-android/claude-md-templates) give you markdown rules to copy; this repo adds an executable 3-gate runner and 83 committed tests, not just instructions.
- [Claude Code starter setups](https://github.com/centminmod/my-claude-code-setup) configure memory banks and settings; this repo is a per-project workflow template with a human-approval gate and measured evidence docs.
- [Mini-harness tutorials](https://github.com/truongpx396/learn-harness-engineering-by-building-mini-claude-code) teach agent-loop engineering but require model SDKs and API keys; this repo runs offline on the standard library.
- [Minimal Python cookiecutters](https://github.com/Techcable/cookiecutter-python-minimal) scaffold packaging (setuptools, linters); this repo scaffolds the design → implement → verify loop instead, with no packaging files at all.

## FAQ

**Does it really have zero dependencies?**
Yes. There is no `pyproject.toml`, `setup.py`, or `requirements.txt`; every import in `scripts/` and `tests/` is from the Python standard library. Check with `grep -rh "^import \|^from " scripts/ tests/ | sort -u`.

**What do the three gates check?**
`deterministic` runs the unit suite, `critic` runs the adversarial regression suite, and `debloat` runs `scripts/check_loc.py` to reject code growth versus the pinned base commit. The runner stops after the first failing gate.

**Why does the report always say `human_approval: pending`?**
Because passing gates mean "ready for human review", never "approved". A person still checks spec conformance and merges. Software in this repo cannot grant approval.

**Does it work on Windows?**
Yes, with `python` instead of `python3`. The review-fix stage runs the suite on Windows too; Windows-specific path and executable-lookup regressions run there, while the newline-filename regression is skipped (Windows filenames cannot contain newlines). macOS has not been tested.

**Where do I start a new task?**
Copy `specs/TEMPLATE_spec.md`, fill in goals and acceptance tests, implement, then point the gate commands at your real checks. See [Work on a new task](#work-on-a-new-task).

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
`{python}` to select the interpreter running the harness. Configuration/report
paths and relative executable paths with a directory part (such as
`bin/tool.exe`) are resolved against the repository root. Bare executable names
are searched on PATH; commands also run with the repository root as their cwd.

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
review-fix commit and grew further in later fixes, so a 20% reduction
requirement is premature. `check_loc.py` still defaults to 20% as required by
CLAUDE.md Gate 3. When a real debloating pass starts, set this repository's
minimum to 20% and compare against the commit before that pass.

The baseline is the commit pinned in `verification.json` (the latest review-fix
commit), with `--min-percent 0`. The PM repins it after each round of fixes.
This follows the owner's decision to prohibit growth relative to the fix commit,
including the safety fixes in the baseline rather than claiming they reduced code.
After repinning, all three gates must pass for unchanged code. `docs/RESULTS.md`
records actual executions before and after PM repinning.
The counter counts LF, CRLF and CR-only line endings, including mixed endings.
Its default `:(icase)*.py` pathspec includes `.PY` and other case variants,
excluding `tests/`. Blank and `#`-only lines are excluded.
Counted files at the base commit and in the worktree with a non-UTF-8 encoding
declaration in the first two lines are rejected with exit code 2 and their path.
UTF-8 aliases and the tokenizer's `utf-8-*` names, including `utf-8-unix` and
`utf-8-dos`, are allowed. Git color and column output are explicitly disabled;
unparsed output from the declaration check returns exit 2.
Removing the earlier `git grep -I` exclusion fixed the `.gitattributes`
binary/`-diff` bypass; adding `-a` was not what fixed that omission.
Non-ignored untracked Python files count, but nested untracked repositories,
ignored files and excluded paths do not. Git execution, timeout, decoding and
numeric-conversion errors exit with code 2; grep failures also print a diagnostic
containing the exit code. Unmatched LF count output contributes zero lines.

## Trust boundaries

Review every config before running it. Its argv arrays are executable
instructions with your account's permissions. `shell=False` prevents incidental
shell parsing; it does not make a command safe. No command denylist, sandbox,
credential protection or network isolation is implemented by this runner.
Repository Python modules are also trusted: a root-level `unittest.py` can
shadow the standard library in a `python -m unittest` gate. Safe executable
lookup does not isolate Python imports.

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
Batch paths ending in a dot (after trailing spaces are stripped) or beginning
with `\\?\` are rejected before execution with `launch_error`. Case-insensitive
extension checks also protect uppercase PATHEXT results such as `tool.CMD`.
Hijacking tests remove `NoDefaultCurrentDirectoryInExePath` from the environment
used for the attack so an OS lookup restriction cannot mask a regression.
`docs/RESULTS.md` records both unittest commands with the variable set to `1`
and removed.

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
