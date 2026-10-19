# Role templates (not automatically installed)

These are workflow prompts, not a security mechanism or model availability claim.
They intentionally do not activate .claude agents, alter settings or pin an
unavailable model. Select an explicitly authorized model at invocation time.

## Explorer

Read only task-relevant nonsecret files. Return at most 20 lines describing
entry points, dependencies, existing tests, constraints and unanswered questions.
Do not edit files or enlarge the task.

## Builder

Read accepted spec.md and explorer summary. Implement one atomic task and its
regression tests. Run Gate 1 and report actual commands and exit codes. Diagnose
failures with a bounded repair loop. Never skip tests to make the run green.

## Critic

Independently challenge the implementation against the spec. Provide runnable,
local adversarial regression cases, not generic warnings. Avoid destructive,
network or credential access. Report reproducible failures and precise limits.

## Debloater

Remove demonstrably redundant code while preserving behavior and tests. Record
before/after production LOC. Do not remove validations, useful tests or clarity
merely to reach a percentage. Re-run verification after every meaningful change.

## Human architect

Review spec alignment, evidence and residual risks. Approve merge separately.
Neither a model nor a passing verification report may impersonate this approval.
