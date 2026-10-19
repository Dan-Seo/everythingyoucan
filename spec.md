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

A UTF-8 JSON object with exactly `version` (integer 1) and `gates` (array of
three objects). Gates must appear in order: `deterministic`, `critic`, `debloat`.
Each object contains exactly `name`, `argv`, and `timeout_seconds`. `argv` is a
nonempty list of nonempty strings without NUL characters or unpaired surrogate code points. The exact token
`{python}` is replaced with the current Python executable. Timeout is a finite
number greater than zero and at most 3600; booleans are not numbers here.
Unknown fields, duplicate JSON keys, malformed JSON and excess input (>64 KiB)
are rejected before any command runs. Configurations are trusted executable
instructions; this tool is not a sandbox or a security policy.

## Behavior and output schema

Commands run sequentially from the repository root without a shell. The first
nonzero exit, timeout or launch failure stops execution. Output is inherited by
the terminal, not captured in memory. The JSON report contains version, overall
status, human_approval (`pending`), and ordered gate results including name,
status and exit_code (null when unavailable). Gate statuses are passed, failed,
timed_out, launch_error or not_run. Overall status is passed only when all three
gates passed, but this means ready for human review, never approved or merged.
Reports are written atomically in the chosen report directory after commands
finish. The report target must not overwrite configuration or a tracked source
file or Git metadata (including linked-worktree/common metadata directories); default output is .artifacts/verification.json. Errors to stderr and exit
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

## Deterministic acceptance criteria

1. `python3 -m unittest discover -s tests -v` exits 0 without third-party packages.
2. `python3 scripts/verify.py --config verification.json` exits 0 on this starter.
3. Tests cover malformed/oversized schema, duplicate keys, booleans/nonfinite
   timeouts, gate ordering, success/failure ordering, timeout and launch failure,
   human approval invariant, atomic report output and protected output targets.
4. Critic cases are committed tests, not an assertion that all bugs are absent.
5. Debloat review records actual simplifications; no arbitrary LOC reduction
   that weakens validation or tests to hit a quota.
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
