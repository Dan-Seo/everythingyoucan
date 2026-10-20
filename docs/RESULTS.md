# Measured results

Post-third-round validation executed on 2026-10-20, Windows 11 (10.0.26200),
Python 3.13.9 (`C:\Users\emper\anaconda3\python.exe`), Git 2.54.0.windows.1.
All times below are local Asia/Seoul (UTC+09:00), on that date.
Working directory: `C:\Users\emper\Desktop\everythingyoucan-review-fixes`.
Code/test commit and debloat baseline:
`5e4471e9dc4a1d2d3559868abb151b3313c4c697`;
minimum reduction: **0%**. The script's default remains 20%.
The owner chose to prohibit growth relative to the third review-fix commit;
the reset includes the safety additions in the baseline and claims no reduction.
Only configuration and documentation changed in this post-commit update.
Hashes of all four Python files in `scripts/` and `tests/` were identical before
and after validation.

The parent process did not have `NoDefaultCurrentDirectoryInExePath` set.
For comparison, each unittest command ran once with that variable explicitly
set to `1` in its child environment and once with the variable removed
case-insensitively. The harness inherited the parent environment (variable absent).
The parent and persistent user environment were not changed. Hijacking tests
also remove the variable themselves when exercising the attack.

## Commands actually executed

| Command | Variable in child environment | Start (+09:00) | End (+09:00) | Exit | Tests reported | Passed | Skipped |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `python -m unittest discover -s tests` | `1` | 14:06:16.320 | 14:06:47.080 | 0 | 72 | 71 | 1 |
| `python -m unittest tests.test_adversarial` | `1` | 14:06:47.081 | 14:07:08.021 | 0 | 43 | 42 | 1 |
| `python -m unittest discover -s tests` | Removed | 14:07:08.022 | 14:07:36.906 | 0 | 72 | 71 | 1 |
| `python -m unittest tests.test_adversarial` | Removed | 14:07:36.907 | 14:07:57.498 | 0 | 43 | 42 | 1 |
| `python scripts/verify.py --config verification.json` | Inherited: absent | 14:07:57.499 | 14:08:28.906 | 0 | 29 + 43 across two test gates | 71 | 1 |

Counts include skipped tests, as reported by unittest. The commands rerun
overlapping tests; their counts are not distinct-test totals. No test failures
or errors occurred. Raw stdout/stderr, command metadata and a JSON execution
summary are retained locally in
`C:\Users\emper\AppData\Local\Temp\astra-round3-evidence-5ma6dq3p`
(`set-discover.txt`, `set-adversarial.txt`, `removed-discover.txt`,
`removed-adversarial.txt`, `verify.txt`, `results.json`).

## Skipped test

Each of the five executions skipped the same test once:
`AdversarialTests.test_real_worktree_with_newline_parent_path`
in `tests/test_adversarial.py`.
The existing platform condition skips it on Windows with the reason:
`Windows file names cannot contain newlines`.
All Windows-specific regressions passed, including uppercase batch lookup,
repository-relative executables and unsupported batch paths.
The report-symlink test ran and passed; it was not
skipped for lack of privilege.

## Verification gates

| Gate | Status | Exit | Observed result |
| --- | --- | --- | --- |
| deterministic | passed | 0 | 29 tests passed; none skipped |
| critic | passed | 0 | 43 tests reported: 42 passed, 1 skipped as described above |
| debloat | passed | 0 | 232 baseline code lines → 232 current code lines; reduction 0.0%, required 0% |

The debloat gate actually ran the following command through the current Python
interpreter; it was not a separate top-level invocation:

```text
{python} scripts/check_loc.py --base 5e4471e9dc4a1d2d3559868abb151b3313c4c697 --min-percent 0
```

Its output was:

```text
code lines 232 at 5e4471e9dc4a1d2d3559868abb151b3313c4c697 -> 232 now; reduction 0.0% (required 0%)
```

The count uses the default `:(icase)*.py` pathspec, excluding `tests/`,
blank lines and `#`-only comments. LF, CRLF and CR-only lines count, including
mixed endings, and extension case variants such as `.PY` are included.
Removing the earlier `git grep -I` exclusion fixed the binary/`-diff`
attribute bypass; adding `-a` was not what fixed the omission.
Non-ignored untracked files count; nested untracked repositories and ignored
files remain outside the count. Git output-parsing failures return exit 2,
and failed grep calls also print an exit-code diagnostic.
No code reduction is claimed.
The generated report is `.artifacts/verification.json`, with overall
`status: passed`, `human_approval: pending`, and all three gate exit codes 0.
Its bytes were checked to contain LF line endings with no CR bytes.
The earlier CRLF report had already been moved by the PM; this update deleted
no report. Users with
an old CRLF report must choose a new path or manually move/remove it.

## Historical evidence and limits

Stage 2 on the same date used baseline
`7358761d30cab9cf6f03f6e5fadf3e62342319b1`: discover reported 47 tests,
adversarial reported 27, and the harness ran 20 + 27 tests with a 215 → 215
line count. All three exited 0, each with one skipped test. The subsequent
independent verification still returned FAIL; those green commands did not
cover every defect. `REVIEW.md` records the findings and second-round fixes.

The earlier validation against second-round baseline
`912dd6af7e4a298a356eab47c65fe243244e88c8` reported 60 tests (59 passed,
1 skipped), 36 adversarial tests (35 passed, 1 skipped), and harness gates
24 + 36 with 221 → 221 code lines. Both environment variants of the unittest
commands and the inherited-environment harness exited 0. Its raw evidence
remains in `C:\Users\emper\AppData\Local\Temp\astra-stage3-2z0qhml5`.
Verifier2 subsequently returned PASS-WITH-NOTES on `c823171..07a4cf5`;
`REVIEW.md` records each note's disposition in the third-round fixes.

These observations apply to this Windows run. Linux, macOS, ZIP distribution
and patch distribution checks, the independent verifier's standalone attack
scripts, and mutation checks were not rerun in this update. Earlier mutation
evidence, including the five third-round tests before CR integration, is
distinguished from these current executions in `REVIEW.md`.
Root Python modules such as `unittest.py` may shadow the standard library in
`python -m` gates. Passing gates do not remove that trust boundary, the
same-LF-prefix ambiguity, nested/ignored-file count limits or TOCTOU limitation,
grant merge approval, or constitute a new independent verification verdict.
