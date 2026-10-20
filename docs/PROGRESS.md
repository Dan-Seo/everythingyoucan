# Progress

Implementation and local regression tests exist on the local template branch.
See `REVIEW.md` for provenance, review-fix status and limitations. `RESULTS.md`
contains historical results and remains unchanged until the PM commits the
review fixes and separately instructs baseline SHA pinning and a results update.
For now, `--base HEAD --min-percent 0` intentionally fails on the added safety
code; deterministic and critic must pass. Human merge approval remains pending.

The original CLAUDE.md and .claude/settings.json remain unchanged. Inactive role
prompts live in docs/roles.md, not in an installed or activated agent setup.
