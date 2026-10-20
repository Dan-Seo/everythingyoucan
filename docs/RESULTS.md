# Measured results

Stage 3 executed on 2026-10-20, Windows 11 (10.0.26200), Python 3.13.9
(`C:\Users\emper\anaconda3\python.exe`).
All times below are local Asia/Seoul (UTC+09:00), on that date.
Working directory: `C:\Users\emper\Desktop\everythingyoucan-review-fixes`.
Code/test commit and debloat baseline:
`912dd6af7e4a298a356eab47c65fe243244e88c8`;
minimum reduction: **0%**. The script's default remains 20%.
The owner chose to prohibit growth relative to the second review-fix commit;
the reset includes the safety additions in the baseline and claims no reduction.
Only configuration and documentation changed in stage 3.

The parent process did not have `NoDefaultCurrentDirectoryInExePath` set.
For comparison, each unittest command ran once with that variable explicitly
set to `1` in its child environment and once with the variable removed
case-insensitively. The harness inherited the parent environment (variable absent).
The parent and persistent user environment were not changed. Hijacking tests
also remove the variable themselves when exercising the attack.

## Commands actually executed

| Command | Variable in child environment | Start (+09:00) | End (+09:00) | Exit | Tests reported | Passed | Skipped |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `python -m unittest discover -s tests` | `1` | 12:55:04.590713 | 12:55:27.231531 | 0 | 60 | 59 | 1 |
| `python -m unittest tests.test_adversarial` | `1` | 12:55:27.232540 | 12:55:48.134833 | 0 | 36 | 35 | 1 |
| `python -m unittest discover -s tests` | Removed | 12:55:48.135807 | 12:56:11.391455 | 0 | 60 | 59 | 1 |
| `python -m unittest tests.test_adversarial` | Removed | 12:56:11.392413 | 12:56:27.490790 | 0 | 36 | 35 | 1 |
| `python scripts/verify.py --config verification.json` | Inherited: absent | 12:56:27.491642 | 12:56:52.028388 | 0 | 60 across two test gates | 59 | 1 |

Counts include skipped tests, as reported by unittest. The commands rerun
overlapping tests; their counts are not distinct-test totals. No test failures
or errors occurred. Raw stdout/stderr, command metadata and a JSON execution
summary are retained locally in
`C:\Users\emper\AppData\Local\Temp\astra-stage3-2z0qhml5`
(`set-discover.txt`, `set-adversarial.txt`, `removed-discover.txt`,
`removed-adversarial.txt`, `verify.txt`, `results.json`).

## Skipped test

Each of the five executions skipped the same test once:
`AdversarialTests.test_real_worktree_with_newline_parent_path`
in `tests/test_adversarial.py`.
The existing platform condition skips it on Windows with the reason:
`Windows file names cannot contain newlines`.
All 16 Windows-specific adversarial tests passed: 15 in
`WindowsAdversarialTests` and `test_check_loc_git_ignores_caller_cwd` in
`LineCountAdversarialTests`. The report-symlink test ran and passed; it was not
skipped for lack of privilege.

## Verification gates

| Gate | Status | Exit | Observed result |
| --- | --- | --- | --- |
| deterministic | passed | 0 | 24 tests passed; none skipped |
| critic | passed | 0 | 36 tests reported: 35 passed, 1 skipped as described above |
| debloat | passed | 0 | 221 baseline code lines → 221 current code lines; reduction 0.0%, required 0% |

The debloat gate actually ran the following command through the current Python
interpreter; it was not a separate top-level invocation:

```text
{python} scripts/check_loc.py --base 912dd6af7e4a298a356eab47c65fe243244e88c8 --min-percent 0
```

Its output was:

```text
code lines 221 at 912dd6af7e4a298a356eab47c65fe243244e88c8 -> 221 now; reduction 0.0% (required 0%)
```

The count uses the script's default Python pathspecs, excluding `tests/`,
blank lines and `#`-only comments. `git grep -a` prevents binary/`-diff`
attributes from hiding matching files; non-ignored untracked files count.
No code reduction is claimed.
The generated report is `.artifacts/verification.json`, with overall
`status: passed`, `human_approval: pending`, and all three gate exit codes 0.
Its bytes were checked to contain LF line endings without CRLF. The PM had
already moved the previous CRLF report; stage 3 did not delete it. Users with
an old CRLF report must choose a new path or manually move/remove it.

## Historical evidence and limits

Stage 2 on the same date used baseline
`7358761d30cab9cf6f03f6e5fadf3e62342319b1`: discover reported 47 tests,
adversarial reported 27, and the harness ran 20 + 27 tests with a 215 → 215
line count. All three exited 0, each with one skipped test. The subsequent
independent verification still returned FAIL; those green commands did not
cover every defect. `REVIEW.md` records the findings and second-round fixes.

These observations apply to this Windows run. Linux, macOS, ZIP distribution
and patch distribution checks, the independent verifier's standalone attack
scripts, and mutation checks were not rerun in this stage. The four added
protection tests' mutation results are second-round evidence in `REVIEW.md`.
Passing gates do not remove the same-LF-prefix ambiguity or TOCTOU limitation,
grant merge approval, or constitute a new independent verification verdict.
