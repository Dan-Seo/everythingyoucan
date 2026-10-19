# Measured results

Recorded 2026-10-19 UTC on Linux, Python 3.12.14.

- `python3 -m unittest discover -s tests -v`: 23 tests, exit **0**.
- `python3 scripts/verify.py --config verification.json`: exit **0**.
  - deterministic subset: 12 tests, exit 0.
  - adversarial subset: 11 tests, exit 0.
  - automated syntax/LOC check: exit 0.
  - report overall status: passed; human_approval: **pending**.
- `python3 scripts/check_scope.py`: exit **0**.
- `git diff --exit-code -- CLAUDE.md .claude/settings.json`: exit **0**.

Production Python lines: initial integration 182 (171 runner + 11 scope check),
final 191 (180 runner + 11 scope check), increase 9 due to concrete protections.
Two unused test imports removed. No percentage reduction claimed.

Original-file SHA-256 checksums:

- CLAUDE.md: bc2282b8d0839dd1b700a196236feb29efb5dd162929f794a014548267dad051
- .claude/settings.json: 2d11f21d3fb4ec9bc8f2edbbb7b1a8fda68fd61bda3e72b14439e5b81631d641

These results are local observations, not a guarantee that future edits pass.
No external Claude source critique completed; independent native review found
three concrete defects, all fixed with regression tests. No merge/push/deploy.

## Distribution checks

The source ZIP was extracted into a fresh temporary directory. `git init`,
`git add .`, the 23-test suite and full harness each exited 0. The separate
patch passed `git apply --check` (exit 0) against an original-file-only
checkout; applying it, indexing the files and running all tests also exited 0.
The ZIP integrity check passed. Neither artifact includes .git, caches, runtime
reports, credentials, private model transcripts or opaque thinking signatures.
