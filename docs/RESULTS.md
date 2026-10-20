# Measured results

Post-fifth-round validation executed on 2026-10-20, Windows 11 (10.0.26200),
Python 3.13.9 (`C:\Users\emper\anaconda3\python.exe`), Git 2.54.0.windows.1.
All times below are local Asia/Seoul (UTC+09:00), on that date.
Working directory: `C:\Users\emper\Desktop\everythingyoucan-review-fixes`.
Code/test commit and debloat baseline:
`0b51aa10ac7c241e66927de5b835dc089edb9b60`;
minimum reduction: **0%**. The script's default remains 20%.
The owner chose to prohibit growth relative to the fifth review-fix commit;
the reset includes the safety additions in the baseline and claims no reduction.
Only configuration and documentation changed in this post-commit update.
Besides the baseline, the PM raised the critic gate's `timeout_seconds` from
60 to 120: the suite grew to 54 tests (about 45 seconds here), and both the
fourth verifier and the fifth-round builder saw it exceed 60 seconds under load.
Hashes of all four Python files in `scripts/` and `tests/` were identical before
and after validation.

The parent process had `NoDefaultCurrentDirectoryInExePath=1` set.
For comparison, each unittest command ran once with that variable explicitly
set to `1` in its child environment and once with the variable removed
case-insensitively. The harness inherited the parent environment (variable `1`).
The parent and persistent user environment were not changed. Hijacking tests
also remove the variable themselves when exercising the attack.

## Commands actually executed

| Command | Variable in child environment | Start (+09:00) | End (+09:00) | Exit | Tests reported | Passed | Skipped |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `python -m unittest discover -s tests` | `1` | 20:39:13.061 | 20:40:05.235 | 0 | 83 | 82 | 1 |
| `python -m unittest tests.test_adversarial` | `1` | 20:40:05.341 | 20:40:50.092 | 0 | 54 | 53 | 1 |
| `python -m unittest discover -s tests` | Removed | 20:40:50.153 | 20:41:41.499 | 0 | 83 | 82 | 1 |
| `python -m unittest tests.test_adversarial` | Removed | 20:41:41.563 | 20:42:26.621 | 0 | 54 | 53 | 1 |
| `python scripts/verify.py --config verification.json` | Inherited: `1` | 20:42:26.885 | 20:43:19.165 | 0 | 29 + 54 across two test gates | 82 | 1 |

Counts include skipped tests, as reported by unittest. The commands rerun
overlapping tests; their counts are not distinct-test totals. No test failures
or errors occurred. Raw stdout/stderr, command metadata and a JSON execution
summary are retained locally in
`C:\Users\emper\AppData\Local\Temp\claude\C--Users-emper-Desktop-everythingyoucan\768b4c62-288a-45ea-8dea-d4e03c44dfa5\scratchpad\pm-round5-evidence`
(`set-discover.txt`, `set-adversarial.txt`, `removed-discover.txt`,
`removed-adversarial.txt`, `verify.txt`, `repro-utf7.txt`, `repro-gitconfig.txt`).
Both reproduction scripts cloned `0b51aa1`: with 600 statements hidden behind a
UTF-7 declaration, the configured harness exited 1 with the debloat gate at
exit 2 and the default-20% counter exited 2, with no Git settings and with local
`grep.column=true`, `color.ui=always`, `color.grep=always` or global
`color.ui=always`.

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
| critic | passed | 0 | 54 tests reported: 53 passed, 1 skipped as described above |
| debloat | passed | 0 | 258 baseline code lines → 258 current code lines; reduction 0.0%, required 0% |

The debloat gate actually ran the following command through the current Python
interpreter; it was not a separate top-level invocation:

```text
{python} scripts/check_loc.py --base 0b51aa10ac7c241e66927de5b835dc089edb9b60 --min-percent 0
```

Its output was:

```text
code lines 258 at 0b51aa10ac7c241e66927de5b835dc089edb9b60 -> 258 now; reduction 0.0% (required 0%)
```

The count uses the default `:(icase)*.py` pathspec, excluding `tests/`,
blank lines and `#`-only comments. LF, CRLF and CR-only lines count, including
mixed endings, and extension case variants such as `.PY` are included.
Removing the earlier `git grep -I` exclusion fixed the binary/`-diff`
attribute bypass; adding `-a` was not what fixed the omission.
Non-ignored untracked files count; nested untracked repositories and ignored
files remain outside the count. Decoding and numeric-conversion failures, unparsed encoding-header output and
non-UTF-8 encoding declarations return exit 2, and failed grep calls also print an exit-code diagnostic.
No code reduction is claimed.
The generated report is `.artifacts/verification.json`, with overall
`status: passed`, `human_approval: pending`, and all three gate exit codes 0.
Its bytes were checked to contain LF line endings with no CR bytes.
The earlier CRLF report had already been moved by the PM; this update deleted
no report. Users with
an old CRLF report must choose a new path or manually move/remove it.

## Fourth-round fixes and validation

Executed on 2026-10-20 in the same worktree and Windows/Python environment,
starting from `943c4c8655bc365f75fc757259a39d3bbb0bce39` with uncommitted fixes.
Only `scripts/check_loc.py`, the two test files, README and this document changed.
`scripts/verify.py` and `verification.json` were not edited.

The line counter now checks the counted files at both the base commit and the
worktree for non-UTF-8 PEP 263 declarations. It reads the first two LF records
with Git, then splits CR/CRLF too before checking the first two Python lines.
Non-UTF-8 declarations return exit 2 with the offending path; normalized UTF-8
aliases remain allowed. Declarations after line two are ignored. README now
limits the parsing-error claim to decoding and numeric conversion; unmatched
LF count output still contributes zero lines.

The four encoding tests were written and executed before the implementation:
`test_non_utf8_encoding_cookies_cannot_hide_worktree_code`,
`test_non_utf8_encoding_cookies_are_rejected_at_base`,
`test_utf8_encoding_cookies_are_allowed`, and
`test_encoding_cookies_after_second_line_are_ignored`.
The red run reported 4 tests, exit 1, and 25 failing subtests/assertions:
worktree payloads returned 0 instead of 2, and the encoded base returned 1
instead of 2. The two allow/ignore tests already passed. After the fix, the
focused run containing these four tests and six related regressions reported
10 tests, exit 0, `OK`, with no skips.

| Command | Variable in child environment | Start (+09:00) | End (+09:00) | Exit | Tests reported | Passed | Skipped |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `python -m unittest discover -s tests` | `1` | 14:59:36.981 | 15:00:32.263 | 0 | 76 | 75 | 1 |
| `python -m unittest tests.test_adversarial` | `1` | 15:00:32.264 | 15:01:05.750 | 0 | 47 | 46 | 1 |
| `python -m unittest discover -s tests` | Removed | 15:01:05.751 | 15:01:50.175 | 0 | 76 | 75 | 1 |
| `python -m unittest tests.test_adversarial` | Removed | 15:01:50.176 | 15:02:37.459 | 0 | 47 | 46 | 1 |

Each execution skipped only the existing Windows newline-filename test named
above. Counts include skips and overlapping executions are not distinct totals.
Only child environments were changed; the parent variable was absent.

`python scripts/verify.py --config verification.json` also ran in this worktree,
15:02:23.509 to 15:03:19.981 (+09:00), with the variable absent. The two test
gates produced these results:

| Gate | Status | Exit | Tests reported | Passed | Skipped |
| --- | --- | --- | --- | --- | --- |
| deterministic | passed | 0 | 29 | 29 | 0 |
| critic | passed | 0 | 47 | 46 | 1 |

The two repaired regression tests also ran in external copies of `scripts/`
and `tests/`, without mutating the worktree scripts. The batch delimiter test
uses a temporary path without whitespace, asserted by the test. The Git lookup
test plants a `cmd.exe` copy as `git.exe`, supplies a marker-writing command on
stdin, and directly asserts that the marker was not created.

| External copy | Variable `1` | Variable removed | Observed result |
| --- | --- | --- | --- |
| Unmodified control | Exit 0; 2 tests | Exit 0; 2 tests | Both repaired tests passed |
| Batch path quoting removed | Exit 1; 1 test | Exit 1; 1 test | 88 failed subtests in each run |
| Git grep changed to bare `git` | Exit 1; 1 test | Exit 1; 1 test | Marker detected: `the planted git.exe ran` |

The supplied `python -I .../repro_utf7_loc_evasion.py` was executed unchanged
(script exit 0).
It clones committed HEAD, so that invocation exercised the pre-fix code rather
than these uncommitted changes. After the PM committed `73e2d98`, the same
script cloned that commit: 600 hidden statements still ran under Python, but the
configured harness exited 1 with the debloat gate at exit 2, and the default-20%
counter exited 2. Its generated attack file still executed 600
added statements. After applying the current counter and tests to that same
temporary clone, the default-20% counter exited 2 and printed
`debloat gate: non-UTF-8 encoding declaration in scripts/verify.py`.
Running the configured verification command in that clone also passed both
test gates (29 and 47 tests, exits 0); its configured line-counter gate rejected
the same payload with exit 2.

Raw red/green, environment-variant, mutation and reproduction outputs and JSON
metadata are retained in
`C:\Users\emper\AppData\Local\Temp\sol-round4-evidence-fswaj2dq`.
Full harness status and baseline figures are reserved for the PM's post-commit
baseline update. Linux/macOS and unrelated standalone attacks were not rerun.

## Fifth-round fixes and validation

Executed on 2026-10-20 in the same worktree and Windows/Python environment,
starting from `2f699b3` with uncommitted fixes. The counter, adversarial tests,
README, spec and four evidence/progress documents changed. `scripts/verify.py`,
`tests/test_verify.py` and `verification.json` were not edited. The PM owns
committing and repinning; the current-results tables above remain unchanged.

The shared Git grep command now passes `--no-color` and `--no-column`.
The declaration pass rejects any bytes left outside complete header records,
including nonempty output with no parsed records, with exit 2 and a diagnostic.
Empty, blank, comment-only and unterminated files still work. UTF-8 names
starting with `utf-8-` after case/underscore normalization are allowed, matching
the Python tokenizer, while the existing non-UTF-8 rejection tests still pass.
Descriptions of the current baseline now refer to the commit pinned in
`verification.json` (the latest review-fix commit); historical commit numbers
are preserved. REVIEW, the Korean summary and PROGRESS include rounds 4 and 5.

Seven tests were added in `LineCountAdversarialTests` before implementation:

- `test_git_output_settings_cannot_hide_encoding_cookies`
- `test_unparsed_encoding_headers_are_execution_errors`
- `test_utf8_tokenizer_suffix_cookies_are_allowed`
- `test_valid_encoding_headers_allow_empty_and_unterminated_files`
- `test_non_utf8_cookie_spellings_cannot_hide_code`
- `test_gitattributes_cannot_hide_encoding_cookies`
- `test_formfeed_and_vertical_tab_indentation_count`

The focused red run reported 7 tests, exit 1, `FAILED (failures=18)`:
six local/temporary-global settings allowed the UTF-7 payload (exit 0 instead
of 2, `100 -> 1`, 99.0% reduction); four malformed header outputs silently
passed (exit 0 instead of 2); eight UTF-8 suffix/position combinations were
rejected (exit 2 instead of 0). The four existing-behavior tests already passed.
After the minimal counter fix, the identical focused command reported 7 tests,
exit 0, `OK`, with no skips. Exact argv and outputs are in `red.json`, `red.txt`,
`green.json` and `green.txt` under the evidence directory below.

The Git-setting test covers `grep.column=true`, `color.ui=always` and
`color.grep=always` separately, both locally and through `GIT_CONFIG_GLOBAL`.
Each setting checks correct ordinary-file counts as well as payload rejection.
The global configuration is a test-owned temporary file; the user's global
configuration was not changed. Declaration spelling tests cover CR/CRLF blank
first lines, whitespace/form feed, `coding=`, Vim's `fileencoding=`, tabs and
multiple spaces after the colon, and two declarations on one line. Attribute
tests combine the payload with `*.py binary` and `*.py -diff`. Indentation
tests cover both `\v` and `\f` under LF, CRLF and CR-only line endings.

| Command | Variable in child environment | Start (+09:00) | End (+09:00) | Exit | Tests reported | Passed | Skipped |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `python -m unittest discover -s tests` | `1` | 20:18:07.911 | 20:18:54.779 | 0 | 83 | 82 | 1 |
| `python -m unittest tests.test_adversarial` | `1` | 20:18:54.780 | 20:19:34.131 | 0 | 54 | 53 | 1 |
| `python -m unittest discover -s tests` | Removed | 20:19:34.132 | 20:20:21.140 | 0 | 83 | 82 | 1 |
| `python -m unittest tests.test_adversarial` | Removed | 20:20:21.141 | 20:21:00.516 | 0 | 54 | 53 | 1 |
| `python scripts/verify.py --config verification.json` | Removed | 20:21:00.517 | 20:21:48.347 | 1 | 29 + 54 | 82 | 1 |

Only child environments changed; the parent variable was absent. Every full
execution skipped only `test_real_worktree_with_newline_parent_path`, for the
existing Windows filename limitation. Counts include skips and overlapping
executions are not distinct totals.

| Gate | Status | Exit | Tests reported or observed result |
| --- | --- | --- | --- |
| deterministic | passed | 0 | 29 passed, none skipped |
| critic | passed | 0 | 54 reported: 53 passed, 1 skipped |
| debloat | failed | 1 | `252 -> 258`, reduction -2.4%, required 0%; expected before PM repinning |

The generated `.artifacts/verification.json` has overall `status: failed` and
`human_approval: pending`. This is a pre-commit result, not a claim that the
repinned harness passed or that code shrank.

Mutation checks used external copies of the current counter and tests. The
requested substitutions were read from verifier4's unchanged `mutate4.py`
([04], [05], [07], [08], [09], [10], [17], [18], plus [32]). The worktree
scripts were never mutated. Unmodified external controls ran the three
relevant new tests in both environments: 3 tests, exit 0, no skips each.
Each mutant then ran its relevant new test in both environments:

| Mutation | New test | Variable `1` | Variable removed | Failing subtests per run |
| --- | --- | --- | --- | --- |
| [04] Split only on LF | `test_non_utf8_cookie_spellings_cannot_hide_code` | Exit 1 | Exit 1 | 2 |
| [05] Do not split bare CR | Same spelling test | Exit 1 | Exit 1 | 1 |
| [07] Remove whitespace allowance before the break check | Same spelling test | Exit 1 | Exit 1 | 5 |
| [08] Remove whitespace allowance before the declaration | Same spelling test | Exit 1 | Exit 1 | 3 |
| [09] Accept only `coding:` | Same spelling test | Exit 1 | Exit 1 | 2 |
| [10] Accept only one space before the name | Same spelling test | Exit 1 | Exit 1 | 2 |
| [17] Remove declaration-pass `-a` | `test_gitattributes_cannot_hide_encoding_cookies` | Exit 1 | Exit 1 | 2 |
| [18] Greedily select the last declaration | Same spelling test | Exit 1 | Exit 1 | 1 |
| [32] Remove `\v\f` from `CODE_LINE` | `test_formfeed_and_vertical_tab_indentation_count` | Exit 1 | Exit 1 | 6 |

All nine mutations were detected in both environments. For [17], the new
unparsed-output guard already rejects Git's binary-file message with exit 2;
the test fails because the required encoding/path diagnostic is lost. This
mutant does not bypass the new guard. The other declaration mutants accept
payloads, and [32] undercounts indented code. These were focused mutation
checks, not full-suite runs for every mutant.

Both supplied scripts were executed unchanged as `python -I <path>`:
`verifier4/repro/repro_gitconfig_cookie_bypass.py`
and `verifier3/repro/repro_utf7_loc_evasion.py`. Each script exited 0 and cloned
committed HEAD `2f699b3`, so these original invocations exercised the old code.
The Git-config script ran from 20:21:53.119 to 20:25:39.404; the UTF-7 script
ran from 20:25:39.404 to 20:26:16.902 (+09:00). In every payload probe,
Python executed all 600 added statements.

For the Git-config reproduction, an isolated `python -I` wrapper reran the
unchanged original through `runpy`. Immediately after each clone completed,
the wrapper copied only the current `scripts/check_loc.py` and
`tests/test_adversarial.py` into that clone, before the original function
generated its attack. The original script then ran its configured harness and
default-20% counter as written. Neither the supplied source nor the clone's
`verification.json` was edited, and the attack's encoded `scripts/verify.py`
was preserved. The six-case wrapper ran 20:27:08.853 to 20:33:16.410 and exited 0.

| Git-config variant | Committed HEAD: harness / default counter exit | Current fixes: harness / default counter exit |
| --- | --- | --- |
| No setting, variable removed | 1 (debloat 2) / 2 | 1 (debloat 2) / 2 |
| Local `grep.column=true`, variable removed | 0 / 0 | 1 (debloat 2) / 2 |
| Local `color.ui=always`, variable removed | 0 / 0 | 1 (debloat 2) / 2 |
| Local `color.grep=always`, variable removed | 0 / 0 | 1 (debloat 2) / 2 |
| Temporary-global `color.ui=always`, variable removed | 1 (critic 1, debloat not run) / 0 | 1 (debloat 2) / 2 |
| Local `grep.column=true`, variable `1` | 0 / 0 | First run: 1 (critic timed out, debloat not run) / 2; isolated retry: 1 (debloat 2) / 2 |

The old local-setting attacks reported `252 -> 67`, a false 73.4% reduction.
The current first five cases passed both test gates (29 and 54 tests, exits 0)
and rejected the payload at debloat with exit 2. The last case's critic exceeded
the unchanged 60-second limit; its standalone counter still rejected the attack
with exit 2. The evidence driver's assertion flagged that incomplete full flow
(driver exit 1). Only that case was retried in isolation using the unchanged
original `run_variant` function and the same clone-overlay method. The retry
ran 20:34:34.774 to 20:35:42.181, passed 29 and 54 tests with exits 0, reached
debloat exit 2, and returned exit 2 from the default counter; the retry script
exited 0. The original timeout and
the successful retry are both retained. No cause for the timing variation is
claimed, and neither the configuration nor its time limit was changed.

The UTF-7 reproduction's original clone was retained at
`C:\Users\emper\AppData\Local\Temp\v3repror6eq89mu\clone`.
The original invocation already rejected its payload (harness 1, debloat 2,
default counter 2). The same two current files were then overlaid into that
same clone without replacing its encoded attack. From 20:26:16.904 to
20:27:08.465, the configured harness passed both test gates (29 and 54 tests,
exits 0) and rejected the payload at debloat with exit 2 (harness exit 1).
The default counter also exited 2 and printed
`debloat gate: non-UTF-8 encoding declaration in scripts/verify.py`.

Raw command outputs, timestamps and JSON metadata are retained in
`C:\Users\emper\AppData\Local\Temp\sol-round5-evidence-x6jkt0xa`.
Linux/macOS, unrelated standalone attacks and numerical coverage measurement
were not run. Existing line-count, report-prefix, import-shadowing and TOCTOU
limits remain; no new independent verification verdict is claimed.

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
