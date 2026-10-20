# Progress

Implementation and local regression tests exist on the local template branch.
See `REVIEW.md` for provenance, the first independent verification FAIL,
verifier2's PASS-WITH-NOTES and each finding's disposition.
The PM committed the third-round fixes as
`5e4471e9dc4a1d2d3559868abb151b3313c4c697`. This update repins the debloat baseline
to that full SHA with `--min-percent 0`: the owner chose to prohibit growth
relative to the fix commit, not to claim that safety fixes reduced code.
`RESULTS.md` records the three required commands and both unittest commands
with `NoDefaultCurrentDirectoryInExePath` set to `1` and removed.
Human merge approval remains pending.

- On Windows, the counter and test Git calls now share the runner's absolute-PATH
  lookup. Hijacking tests remove `NoDefaultCurrentDirectoryInExePath` themselves.
- Resolved batch executable paths are always double-quoted, preventing delimiter
  splitting while preserving the existing unsafe-character checks. Uppercase
  PATHEXT results such as `tool.CMD` are covered by a regression. Trailing-dot
  and `\\?\` batch paths are rejected before execution with `launch_error`.
- Relative executable paths with a directory part are resolved against the
  repository root, not the caller's working directory.
- Report prefixes are compared as bytes and reports use UTF-8 with LF. Old CRLF
  reports are not overwritten; choose a new path or manually move/remove them.
- The counter includes LF, CRLF and CR-only lines, including mixed endings,
  and matches `.py` extension case variants by default. The earlier removal
  of `git grep -I`, not the addition of `-a`, fixed the `.gitattributes`
  binary/`-diff` bypass.
- Git execution, timeout and output-parsing errors, including decoding and
  numeric conversion, return exit 2. Grep failures also print a diagnostic.
- New tests cover symlinks, post-gate path rechecks, untracked code and zero-line
  baselines; all four corresponding mutations were detected in temporary copies.
- Third-round tests add uppercase batch lookup, worktree grep failure, Git
  timeouts, option-like bases and tree/blob bases. All five corresponding
  mutations were detected before CR integration. The two affected fixtures
  now follow five Git calls; integrated mutation checks have not been repeated.

Other JSON with the same LF prefix remains indistinguishable from a report.
Nested untracked repositories and ignored files remain outside line counts.
Root Python modules such as `unittest.py` can shadow standard-library modules
in `python -m` gates; repository contents are trusted, not import-isolated.
The TOCTOU race between checking and writing also remains. This update changes only
configuration and documentation; it does not change `scripts/` or `tests/`.

The original CLAUDE.md and .claude/settings.json remain unchanged. Inactive role
prompts live in docs/roles.md, not in an installed or activated agent setup.
