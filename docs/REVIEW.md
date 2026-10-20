# Review and evidence

## Scope and provenance

This is the finite template described in `spec.md`, not an application.
Claude Code 2.1.303, resolved model `claude-opus-5-5`, effort `max`, ultracode on,
fast off, supplied the strict schema validator. Its completed response explicitly
said it had not executed the code. Native orchestration integrated the loader,
runner, report writer, CLI, tests and documentation, and executed all checks.
No model-generated code is accepted merely because it was generated.

The broader Claude design/implementation attempts did not yield a completed
artifact. A narrowly scoped validator request did. Do not attribute the entire
project or local test execution to Claude. A subsequent external source critique
was blocked before a completed result; no Claude critique is claimed here.

## Concrete independent review defects fixed

1. A report target such as `.git/HEAD` was not tracked by Git and could pass the
   original tracked-file check. Independent review reproduced corruption in a
   disposable repository. The fix protects `.git`, Git's actual metadata
   directory and common directory, including linked worktrees. Regression tests
   cover metadata targets and confirm the disposable repository remains valid.
2. An unpaired Unicode surrogate in argv passed schema validation but failed
   during process encoding. Validation now rejects surrogate code points before
   any subprocess executes. A regression test verifies no command is started.

3. A follow-up review reproduced a metadata bypass when a repository parent
   path contained a newline. Git directory paths are now queried individually
   and only the terminating newline is removed. A real linked-worktree
   regression covers the newline-containing parent path on platforms that allow
   it; Windows skips this case because filenames cannot contain newlines.

Other adversarial coverage includes huge integer/NaN/infinite timeouts, nested
JSON duplicates, excess nesting, malformed UTF-8, oversized input, literal shell
metacharacters, late-invalid gate fail-before-run, fail-fast side-effect
prevention, and atomic write failure preserving the previous report.

## Review-fix status (2026-10-20)

The accepted work order covers findings 1-6 and 8; finding 7
(`.claude/agents/` and PreToolUse hooks) is out of scope. The statuses below
describe the fixes and accepted limits by topic.

| Topic | Status | Resolution or boundary |
| --- | --- | --- |
| Report overwrite protection and repository size | Fixed | Reject existing non-report files whether tracked, ignored or untracked; read only the report prefix instead of resolving every indexed file. |
| Git metadata aliases | Fixed | Protect worktree and common metadata, including case variants; case-sensitive systems intentionally over-protect those variants. |
| Windows report paths | Fixed | Reject namespace prefixes (`\\?\`, `\\.\`), UNC paths, NTFS alternate streams and components ending in a dot or space. |
| Executable lookup | Fixed | On Windows, search absolute PATH entries and PATHEXT candidates without implicit current-directory lookup; internal Git uses the same resolver. |
| Windows batch execution | Fixed with an intentional limit | `.cmd`/`.bat` paths or arguments containing `& | < > ^ ( ) % ! "` or characters below U+0020 cause `launch_error`; commands requiring them are unsupported. |
| UTF-8 BOM configuration and adversarial module invocation | Fixed | Accept a leading BOM and support `python -m unittest tests.test_adversarial` from the repository root. |
| Newline-parent regression on Windows | Intentional platform limit | Skip only this unsupported filesystem case on Windows; run it elsewhere. |
| Debloat gate | Baseline pinned in stage 2 | `scripts/check_loc.py` keeps its default 20%; this repository uses 0% against `7358761d30cab9cf6f03f6e5fadf3e62342319b1`. |
| Original reverse interview | Recorded process issue | Accepted review-fix decisions are in `spec.md`; code cannot retroactively perform the original interview. |
| Installed agents and PreToolUse hooks | Out of scope | Existing settings and instruction files remain unchanged. |
| Filesystem race between checking and writing | Known limit | Rechecking and atomic replacement do not prevent TOCTOU races. |

## Verification

Run from the repository root:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/verify.py --config verification.json
python3 -m unittest tests.test_adversarial
python3 scripts/check_loc.py --base 7358761d30cab9cf6f03f6e5fadf3e62342319b1 --min-percent 0
```

The first post-fix run executed 22 tests with exit 0; this is historical evidence.
`docs/RESULTS.md` records the actual stage 2 executions against the pinned
review-fix baseline. Use `python` on Windows. Both unittest commands and the
harness must exit 0. The sample harness runs deterministic and
adversarial test subsets separately, followed by the code line count check. A green
third command is not a model simplification judgment or human approval.

## Debloating review

The starter uses functions and standard-library modules, with no dependency
framework, wrapper hierarchy, plugin mechanism or command denylist. Removed two
unused test imports. Production code grew during concrete safety fixes rather
than being artificially shrunk. No 20–30% reduction is claimed. Removing the
metadata check or Unicode validation to meet a quota would be a regression.

No debloating pass has happened yet. This repository alone uses a 0% minimum
to reject growth against the pinned review-fix baseline; `check_loc.py` keeps
its default 20%. A real debloating pass must raise the repository minimum to
20% and compare against the preceding commit. The PM created the review-fix
commit; stage 2 only pins its SHA and records validation.

## Residual limitations

- No sandbox, no network isolation, no descendant-process containment guarantee.
- Report protection is best-effort and not race-proof against a hostile local
  process. Configured commands are explicitly trusted and can mutate any file.
- Existing reports can be stale; report authenticity is not cryptographically
  verified. Concurrent writers must choose distinct paths.
- Historical tests ran on Linux with Python 3.12.14; this review-fix stage also
  validates on Windows. macOS has not been tested.
- The original active settings contain a machine-specific Windows guard path.
  They remain unchanged. No hook was replaced, bypassed or activated by this work.
- No package installation, GitHub push, merge or deployment was performed.
- Human approval remains pending. Passing commands do not certify zero defects.
