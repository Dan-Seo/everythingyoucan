# everythingyoucan

A dependency-free Python starter for the design → implement → verify → human
review workflow described in the original `CLAUDE.md`. This is a template, not an
application, a sandbox, a security certification or an autonomous merge system.

## Quick start

Requires Python 3.10+ and Git. No package installation is needed. Run inside a
Git working tree: report protection queries Git metadata and the index.

For the source ZIP, extract it into a new directory, then initialize and index
that source before using the harness (no commit or network operation is needed):

```sh
git init
git add .
```

Alternatively, overlay the source onto a clone of this repository and run
`git add .` to include new source in tracked-file protection. The accompanying
patch adds the starter files and extends .gitignore while preserving its existing
exclusion. Apply it with `git apply` to the
original clean checkout. Do not apply both the ZIP overlay and the patch.

```sh
python3 -m unittest discover -s tests -v
python3 scripts/verify.py --config verification.json
```

Linux/Python 3.12.14 was tested; Windows/macOS have not been executed. The real
newline-path filesystem regression exercises a Unix-valid filename that Windows
may not support. This is a portability limitation of the current test suite.

On Windows use `python` instead of `python3`. Commands in the configuration use
`{python}` to select the interpreter running the harness. Paths are resolved
relative to the repository, so invoking the script from another directory works.

The runner stops after the first failed gate. Exit codes are 0 for all commands
passing, 1 for a gate failure, and 2 for invalid configuration/report I/O. Output
is streamed to the terminal. The JSON report defaults to
`.artifacts/verification.json`; use `--report path.json` for a different path.
A report always says `human_approval: pending`, even when every command passes.
Existing reports can be stale after an interrupted or invalid run. Check the
current process exit and actual output, not merely the presence of a report.

## What's here

- `spec.md`: implementation scope, exact schema and acceptance criteria.
- `specs/TEMPLATE_spec.md`: copy for a new task before editing code.
- `scripts/verify.py`: strict JSON loading, ordered trusted command execution,
  finite per-command timeout, fail-fast behavior and atomic report replacement.
- `verification.json`: deterministic tests, adversarial regressions and a syntax/
  LOC check. The third command is only an automated scope check; it does not
  replace the simplification review recorded in `docs/REVIEW.md`.
- `docs/roles.md`: inactive role templates, not installed Claude agents.
- `tests/`: standard-library unit and adversarial tests.

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

The runner rejects report targets that would overwrite the config or a tracked
file or Git metadata (including linked-worktree metadata), and checks again after commands execute. This is best-effort correctness,
not protection against a hostile concurrent process or filesystem race.

The original `.claude/settings.json` refers to a machine-specific Windows hook.
It has been deliberately preserved, not repaired, disabled or replaced. This
starter does not make that hook portable. Configure an approved hook separately
before using Claude tools inside the repository. Do not bypass a failing guard.

## Work on a new task

1. Copy the task spec, record assumptions and define concrete acceptance tests.
2. Split work into small isolated changes. Review dependencies before installing.
3. Replace gate argv commands with the task's real checks. Run all tests after
   fixes and simplification; preserve concrete adversarial regression cases.
4. Inspect source, test output and limitations. Ask the human architect for merge
   approval separately. No script here pushes, merges, deploys or calls a model.

See `docs/REVIEW.md` for implementation provenance, measured checks and residual
limits. Passing tests do not mean defect-free software.
