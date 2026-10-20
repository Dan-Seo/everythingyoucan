# Measured results

Stage 2 executed on 2026-10-20, Windows, Python 3.13.9.
All times below are local Asia/Seoul (UTC+09:00), on that date.
Working directory: `C:\Users\emper\Desktop\everythingyoucan-review-fixes`.
Debloat baseline: `7358761d30cab9cf6f03f6e5fadf3e62342319b1`;
minimum reduction: **0%**. The script's default remains 20%.

## Commands actually executed

| Command | Start (+09:00) | End (+09:00) | Exit | Tests reported | Passed | Skipped |
| --- | --- | --- | --- | --- | --- | --- |
| `python -m unittest discover -s tests` | 12:14:46.1017292 | 12:14:53.5011260 | 0 | 47 | 46 | 1 |
| `python -m unittest tests.test_adversarial` | 12:14:53.5021289 | 12:14:56.7529182 | 0 | 27 | 26 | 1 |
| `python scripts/verify.py --config verification.json` | 12:14:56.7539246 | 12:15:05.9092758 | 0 | 47 across two test gates | 46 | 1 |

Counts include skipped tests, as reported by unittest. The commands rerun
overlapping tests; their counts are not distinct-test totals. No test failures
or errors occurred.

## Skipped test

Each command skipped the same test once:
`AdversarialTests.test_real_worktree_with_newline_parent_path`
in `tests/test_adversarial.py`.
The existing platform condition skips it on Windows with the reason:
`Windows file names cannot contain newlines`.
All 13 Windows-specific adversarial tests passed.

## Verification gates

| Gate | Status | Exit | Observed result |
| --- | --- | --- | --- |
| deterministic | passed | 0 | 20 tests passed; none skipped |
| critic | passed | 0 | 27 tests reported: 26 passed, 1 skipped as described above |
| debloat | passed | 0 | 215 baseline code lines → 215 current code lines; reduction 0.0%, required 0% |

The debloat gate actually ran the following command through the current Python
interpreter; it was not a separate fourth top-level invocation:

```text
{python} scripts/check_loc.py --base 7358761d30cab9cf6f03f6e5fadf3e62342319b1 --min-percent 0
```

Its output was:

```text
code lines 215 at 7358761d30cab9cf6f03f6e5fadf3e62342319b1 -> 215 now; reduction 0.0% (required 0%)
```

The count uses the script's default Python pathspecs, excluding `tests/`,
blank lines and `#`-only comments. No code reduction is claimed.
The generated report is `.artifacts/verification.json`, with overall
`status: passed` and `human_approval: pending`.

These observations apply to this Windows run. Linux, macOS, ZIP distribution
and patch distribution checks were not run in this stage. Passing gates do not
remove the documented filesystem race limitation or grant merge approval.
