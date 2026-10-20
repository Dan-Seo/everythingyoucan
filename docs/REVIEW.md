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
| Executable lookup | Fixed in the second review-fix commit | On Windows, search absolute PATH entries and PATHEXT candidates without implicit current-directory lookup; `verify.py`, `check_loc.py` and test Git calls now share the resolver. |
| Windows batch execution | Fixed with intentional limits | Always double-quote the resolved `.cmd`/`.bat` path, including paths without spaces. Paths or arguments containing `& | < > ^ ( ) % ! "` or characters below U+0020 cause `launch_error`. Third-round fixes also reject trailing-dot and `\\?\` batch paths before execution. |
| UTF-8 BOM configuration and adversarial module invocation | Fixed | Accept a leading BOM and support `python -m unittest tests.test_adversarial` from the repository root. |
| Newline-parent regression on Windows | Intentional platform limit | Skip only this unsupported filesystem case on Windows; run it elsewhere. |
| Debloat gate | Baseline repinned after the third-round fixes | `scripts/check_loc.py` keeps its default 20%; this repository uses 0% against `5e4471e9dc4a1d2d3559868abb151b3313c4c697`. |
| Original reverse interview | Recorded process issue | Accepted review-fix decisions are in `spec.md`; code cannot retroactively perform the original interview. |
| Installed agents and PreToolUse hooks | Out of scope | Existing settings and instruction files remain unchanged. |
| Filesystem race between checking and writing | Known limit | Rechecking and atomic replacement do not prevent TOCTOU races. |

## First independent verification FAIL: disposition

The independent verifier evaluated `c823171..cb47ed9` and returned **FAIL**.
Its source report is
`C:\Users\emper\AppData\Local\Temp\claude\C--Users-emper-Desktop-everythingyoucan\768b4c62-288a-45ea-8dea-d4e03c44dfa5\scratchpad\verifier\REPORT.md`.
The numbered findings below match section 5 of that report. The PM committed
the second-round code and test fixes as
`912dd6af7e4a298a356eab47c65fe243244e88c8`; the following configuration and
documentation update recorded execution evidence. Those local results did not replace the
verifier's original verdict or claim a new independent PASS.

| Finding | Status | Change and evidence |
| --- | --- | --- |
| 1. Bare Git calls in the counter and tests | Fixed | `check_loc.py` and both test modules call `_command_path("git")`, sharing the Windows absolute-PATH resolver with `verify.py`. Regression tests exercise planted executables. |
| 2. Batch path delimiters | Fixed | Always double-quote the resolved executable path so `,`, `;`, `=` and Unicode whitespace such as U+00A0 cannot select a different batch file; retain unsafe-character rejection. |
| 3. Environment-dependent hijacking tests | Fixed | Hijacking tests remove `NoDefaultCurrentDirectoryInExePath` in the attack environment. Both unittest commands are also run with the variable set to `1` and removed; see `RESULTS.md`. |
| 4. Report identification | CRLF bypass fixed; LF-prefix ambiguity remains | Compare the prefix as bytes and write UTF-8 reports with literal LF. Other JSON with the exact same LF prefix remains indistinguishable. |
| 5. `.gitattributes` line-count evasion | Fixed; explanation corrected after verifier2 | Removing the earlier `git grep -I` binary-file exclusion fixed the omission at both the base and current revision. Adding `-a` was not what fixed the bypass. |
| 6. Missing protection tests | Fixed | Added tests for dangling report symlinks, post-gate path rechecks, untracked Python code and zero-line baselines. Each passed normally and failed when its protection was removed in a separate temporary copy. |
| 7. Git execution/decoding failures | Fixed | The counter maps Git launch, timeout and output-decoding errors to exit 2; missing-Git and non-UTF-8-output regressions cover this behavior. |
| 8. TOCTOU | Accepted limit; not fixed | The path can still change between checking and writing. Rechecks and atomic replacement do not eliminate that race. |

The four protection-test mutation checks were recorded during the second round
in `C:\Users\emper\AppData\Local\Temp\astra-task2-3h0miweb`.
Old CRLF reports are intentionally no longer eligible for replacement. Use a
new `--report` path or manually move/remove the old report. The PM moved the old
`.artifacts/verification.json` before that earlier update; it performed no
report migration or deletion. This post-third-round update also performs none.

## Second independent verification PASS-WITH-NOTES: disposition

Verifier2 evaluated `c823171..07a4cf5` and returned **PASS-WITH-NOTES**.
Its source report is
`C:\Users\emper\AppData\Local\Temp\claude\C--Users-emper-Desktop-everythingyoucan\768b4c62-288a-45ea-8dea-d4e03c44dfa5\scratchpad\verifier2\REPORT.md`.
The PM committed the third-round code and test fixes as
`5e4471e9dc4a1d2d3559868abb151b3313c4c697`. The following rows match the
eight notes in section 6; section 5's surviving mutations are covered in row 3.
These dispositions and local runs do not constitute a new independent verdict.

| Note | Status | Resolution or remaining boundary |
| --- | --- | --- |
| 1. CR-only line-count evasion | Fixed | Count LF, CRLF and CR-only line endings, including mixed endings. LF counts and CR-led matches are combined. Regressions cover the worktree and CR-only base code. |
| 2. Relative executable uses caller cwd | Fixed | Resolve executable paths with a directory part against the repository root before launch. Bare names still use PATH. A regression plants different executables in the caller and repository directories. |
| 3. Missing protection tests | Tests added | Protect uppercase PATHEXT batch lookup [01], worktree grep failure [18], timeout handling [21], option termination [22], and commit-only bases [23]. The grep fixtures now reflect five Git calls: rev-parse, base LF/CR, worktree LF/CR; timeout cases cover all five. Surviving mutation [17] (`-a` removal) was not a defect in the earlier count implementation. |
| 4. Files omitted from line counts | Partly fixed; limits documented | Default `:(icase)*.py` counts extension case variants such as `.PY`. Nested untracked repositories, ignored files (including `.git/info/exclude`) and excluded paths remain outside the count. |
| 5. Extreme Git output and silent grep failures | Fixed | Numeric conversion and decoding errors return exit 2. Grep failures return exit 2 and print a diagnostic with the failed exit code. Regressions cover extreme numeric output and diagnostics. |
| 6. Root Python modules shadow the standard library | Documented trust boundary | A root-level `unittest.py` can replace the standard library module in `python -m unittest` gates. Repository modules must be trusted; executable lookup protection does not isolate imports. |
| 7. Documentation accuracy and batch-path failure status | Corrected and fixed | Attribute-bypass protection came from removing `-I`, not adding `-a`. Batch paths ending in a dot (after trailing spaces are stripped) or beginning with `\\?\` now produce `launch_error` before execution; a regression verifies this. |
| 8. TOCTOU | Accepted limit; not fixed | Rechecking and atomic replacement do not prevent another process changing a path between validation and writing. |

Before integration of the CR counter, all five added protection tests passed
normally and failed against their corresponding removed-protection mutations
in external copies. Outputs are retained at
`C:\Users\emper\AppData\Local\Temp\astra-task3-mutations-gp91gu0l\results.txt`.
For [22], exit 2 alone remains possible without the delimiter because of
`^{commit}`, so the test also checks the actual Git argument boundary.
After integration, the worktree-failure and timeout fixtures were updated and
the full 29-test deterministic suite passed. Mutation checks were not repeated
against that integrated implementation. Current full-suite evidence is in
`RESULTS.md`.

## Verification

Run from the repository root:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/verify.py --config verification.json
python3 -m unittest tests.test_adversarial
python3 scripts/check_loc.py --base 5e4471e9dc4a1d2d3559868abb151b3313c4c697 --min-percent 0
```

The first post-fix run executed 22 tests with exit 0; this is historical evidence.
`docs/RESULTS.md` records the actual post-commit executions against the third
review-fix baseline, including both Windows environment variants for unittest.
Use `python` on Windows. Both unittest commands and the
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
20% and compare against the preceding commit. The owner explicitly chose to
prohibit growth relative to the fix commit. This update therefore repins the baseline
to the PM's third review-fix commit, including those safety additions in the
baseline rather than measuring them as a reduction.

## Residual limitations

- No sandbox, no network isolation, no descendant-process containment guarantee.
- Report protection is best-effort and not race-proof against a hostile local
  process. Configured commands are explicitly trusted and can mutate any file.
- Python imports are not isolated: repository-root modules such as `unittest.py`
  can shadow the standard library when running `python -m` gates.
- Existing reports can be stale; report authenticity is not cryptographically
  verified. Concurrent writers must choose distinct paths.
- The binary prefix check cannot distinguish another tool's JSON with the same
  LF prefix. Old CRLF reports are rejected rather than automatically migrated.
- Line counts remain a limited metric: nested untracked repositories, ignored
  files, excluded paths and code packed onto fewer lines remain outside what
  the default count detects.
- Historical tests ran on Linux with Python 3.12.14; this review-fix stage also
  validates on Windows. macOS has not been tested.
- The original active settings contain a machine-specific Windows guard path.
  They remain unchanged. No hook was replaced, bypassed or activated by this work.
- No package installation, GitHub push, merge or deployment was performed.
- Human approval remains pending. Passing commands do not certify zero defects.
