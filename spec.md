# Portable architecture starter specification

Status: implementation scope recorded before code; human acceptance pending.

## Goal and assumptions

Turn the existing architecture guidance into a small, dependency-free starter, not
an application. The owner requested autonomous progress while asleep, so missing
product requirements remain explicit rather than inventing a product. Python
3.10+ and Git are the only prerequisites. Preserve the original CLAUDE.md and
.claude/settings.json byte-for-byte. Do not activate or replace security hooks.

## Deliverables

- A standard-library verification runner with strict configuration validation.
- A specimen three-gate configuration, reusable task specification, role guidance,
  regression tests, and honest evidence/report documentation.
- A separate, documented human approval gate which software cannot grant.

## Input schema

A UTF-8 JSON object (a leading BOM is accepted) with exactly `version` (integer 1) and `gates` (array of
three objects). Gates must appear in order: `deterministic`, `critic`, `debloat`.
Each object contains exactly `name`, `argv`, and `timeout_seconds`. `argv` is a
nonempty list of nonempty strings without NUL characters or unpaired surrogate code points. The exact token
`{python}` is replaced with the current Python executable. Timeout is a finite
number greater than zero and at most 3600; booleans are not numbers here.
Unknown fields, duplicate JSON keys, malformed JSON and excess input (>64 KiB)
are rejected before any command runs. Configurations are trusted executable
instructions; this tool is not a sandbox or a security policy.

## Behavior and output schema

Commands run sequentially from the repository root with `shell=False`. A bare
argv[0] (no directory part) is located on PATH. On Windows, only absolute PATH
entries and PATHEXT candidates are searched; the current directory is not
implicitly searched. Internal Git commands use the same lookup. Windows can
implicitly invoke cmd.exe for `.cmd` and `.bat` files even with `shell=False`;
such commands are rejected with `launch_error` if their resolved executable
path or any argument contains `&`, `|`, `<`, `>`, `^`, `(`, `)`, `%`, `!`, `"`,
or a control character below U+0020. Batch commands requiring those characters
are intentionally unsupported. The first
nonzero exit, timeout or launch failure stops execution. Output is inherited by
the terminal, not captured in memory. The JSON report contains version, overall
status, human_approval (`pending`), and ordered gate results including name,
status and exit_code (null when unavailable). Gate statuses are passed, failed,
timed_out, launch_error or not_run. Overall status is passed only when all three
gates passed, but this means ready for human review, never approved or merged.
Reports are written atomically in the chosen report directory after commands
finish. The report target must not be the configuration, Git metadata
(including linked-worktree/common metadata directories, compared without regard
to letter case) or any other existing file except a previous report. A previous
report is recognized when its text starts with what `write_report` emits for a
`run_gates` report (`{`, newline, `  "version": 1,`, newline, `  "status": "`);
only that prefix is read from an existing target. Symlink targets are rejected.
On Windows, namespace prefixes such as `\\?\` and `\\.\`, UNC paths, NTFS
alternate data streams, and path components ending in a dot or space are
rejected. Default output is
.artifacts/verification.json. Errors to stderr and exit
codes: 0 all gates passed; 1 gate failure; 2 invalid configuration or report I/O.
No timestamps or runtime values required: deterministic report structure.

## Edges and boundaries

- Missing executable, negative return codes, invalid UTF-8 and invalid numbers.
- Timeout cleanup terminates and reaps the direct child. Descendants are NOT
  contained or guaranteed terminated on all platforms. Do not run untrusted or
  daemonizing commands. This explicit portable limit is preferable to a false
  sandbox guarantee.
- Ctrl-C interrupts the run; do not interpret existing report files as current
  evidence. Reports are local unsigned claims; inspect exit codes and source.
- No network, credentials, automatic model invocations, package installation,
  automatic hook activation, Git push, merge or deployment in the harness.
- Concurrent runs should use distinct report paths. Atomic replace prevents
  partial JSON but last successful writer wins if the same path is shared.
- Report paths are checked before and after commands run, but replacement of
  files between a path check and a write is not prevented (TOCTOU limitation).

## Deterministic acceptance criteria

1. `python -m unittest discover -s tests` and
   `python -m unittest tests.test_adversarial` both exit 0 from the root without
   third-party packages (use `python3` where appropriate).
2. Run `python scripts/verify.py --config verification.json`. During this
   uncommitted review-fix stage, deterministic and critic must pass; debloat
   is expected to fail with exit 1 because HEAD predates the safety fixes.
   After the PM commits the fixes and pins that SHA in a separately instructed
   step, all gates must pass for unchanged code.
3. Tests cover malformed/oversized schema, duplicate keys, booleans/nonfinite
   timeouts, gate ordering, success/failure ordering, timeout and launch failure,
   human approval invariant, atomic report output and protected output targets,
   Windows path aliases, safe executable lookup and batch-command rejection.
4. Critic cases are committed tests, not an assertion that all bugs are absent.
5. The debloat gate runs `scripts/check_loc.py --base <ref>`: code lines (blank
   and `#`-only lines excluded) in the configured git pathspecs, default `*.py`
   outside `tests/`, must shrink by `--min-percent` (default 20) versus the base
   commit. A missing or invalid base, or zero code lines at the base, fails with
   exit 2. Debloat review still records actual simplifications; no reduction
   may weaken validation or tests to hit a quota.
6. Original instruction and active hook files stay unchanged.

## Planned atomic work

1. Implement strict parser and sequential runner, then report writing and CLI.
2. Add isolated deterministic and adversarial tests using temporary directories.
3. Add example config, documentation, task and agent-role templates.
4. Execute tests, gate harness and syntax checks; review and fix concrete defects.
5. Report exact exit codes and limitations; leave final human gate pending.

## Review clarifications

Independent review found report destinations could clobber Git metadata. The
output protection requirement is clarified to include metadata paths, not just
tracked files. Invalid Unicode scalar argv strings are rejected before execution
to preserve deterministic error handling. These narrow fixes preserve the scope.

## Review fix decisions (2026-10-20)

Recorded from the owner's work order for branch `dot/review-fixes`; these
decisions replace the Phase 1 reverse interview for this round.

- Fix review findings 1-6 and 8. Finding 7 is out of scope. `.claude/agents/`
  and PreToolUse hooks are out of scope and were not created.
- The skipped reverse-interview step of the original work is a past process
  issue; it is recorded here, not fixed in code.
- Windows cannot create file names containing newlines, so the newline-parent
  worktree regression is skipped on Windows only; it still runs elsewhere.
- Report protection now refuses any existing non-report file (tracked, ignored
  or untracked, e.g. `.env`) instead of scanning `git ls-files`. This also
  removes the per-file `resolve()` cost in large repositories. A tracked file
  that is currently deleted from the working tree is no longer protected,
  because writing there overwrites nothing.
- Git metadata is compared case-insensitively. On case-sensitive file systems
  this over-protects names such as `.GIT/x`, which is accepted as safe.
- Windows report-path restrictions, executable lookup and batch-command
  restrictions above are accepted security decisions. The TOCTOU limitation
  remains explicitly outside the protection guarantee.
- No debloating pass has happened yet; `check_loc.py` measures an increase
  from 161 code lines at HEAD to 215. Requiring 20% reduction now would fail.
  This repository alone starts with `--min-percent 0`: unchanged or reduced
  code passes, growth fails. Keep `--base HEAD` at this stage. After committing
  these fixes, the PM will separately instruct pinning that commit's SHA.
  `check_loc.py` retains its default 20% requirement under CLAUDE.md Gate 3.
  When a real debloating pass starts, use its preceding commit as the base and
  raise this repository's minimum to 20%.
- Preserve previous fixes and the staged deletion of the obsolete scope checker.
  Do not edit `scripts/verify.py`, `tests/test_adversarial.py` or
  `docs/RESULTS.md` in this stage. The PM owns commits and later baseline/result
  updates; `.claude/agents/` and PreToolUse hooks remain outside this work.
