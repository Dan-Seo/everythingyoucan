# Progress

Implementation and local regression tests exist on the local template branch.
See `REVIEW.md` for provenance, the first independent verification FAIL and
each finding's disposition. The PM committed the second-round fixes as
`912dd6af7e4a298a356eab47c65fe243244e88c8`. Stage 3 repins the debloat baseline
to that full SHA with `--min-percent 0`: the owner chose to prohibit growth
relative to the fix commit, not to claim that safety fixes reduced code.
`RESULTS.md` records the three required commands and both unittest commands
with `NoDefaultCurrentDirectoryInExePath` set to `1` and removed.
Human merge approval remains pending.

- On Windows, the counter and test Git calls now share the runner's absolute-PATH
  lookup. Hijacking tests remove `NoDefaultCurrentDirectoryInExePath` themselves.
- Resolved batch executable paths are always double-quoted, preventing delimiter
  splitting while preserving the existing unsafe-character checks.
- Report prefixes are compared as bytes and reports use UTF-8 with LF. Old CRLF
  reports are not overwritten; choose a new path or manually move/remove them.
- `git grep -a` prevents binary/`-diff` attributes from hiding matching code.
  Git execution, timeout and output-decoding errors return exit 2.
- New tests cover symlinks, post-gate path rechecks, untracked code and zero-line
  baselines; all four corresponding mutations were detected in temporary copies.

Other JSON with the same LF prefix remains indistinguishable from a report.
The TOCTOU race between checking and writing also remains. Stage 3 changes only
configuration and documentation; it does not change `scripts/` or `tests/`.

The original CLAUDE.md and .claude/settings.json remain unchanged. Inactive role
prompts live in docs/roles.md, not in an installed or activated agent setup.
