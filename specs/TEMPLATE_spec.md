# Task specification

Status: draft / accepted for implementation / ready for human review

## Goal and non-goals

Describe the concrete user outcome. State what is intentionally excluded.

## Questions or authorized assumptions

List missing requirements, edge cases, concurrency and rollback decisions.
If the owner authorized proceeding without questions, record assumptions here.
Do not treat unspecified requirements as approved expansion of scope.

## Inputs and outputs

Define types, required fields, validation, limits, errors and compatibility.

## Security and permissions

List trusted inputs, sensitive data, external destinations and required approvals.
Never call a command filter a sandbox. Never weaken existing guardrails to proceed.

## Atomic implementation steps

Each step must have an owner, bounded file scope and independently testable result.
Use isolated worktrees for concurrent edits to shared code.

## Acceptance tests

List exact commands, expected exit codes and regression cases before implementation.
Include timeout, malformed-input, race and rollback cases where relevant.

## Verification evidence

- Gate 1: commands and actual exit codes.
- Gate 2: reviewer, concrete adversarial cases, defects and regression tests.
- Gate 3: measured changes, simplification and any reason not to reduce LOC.
- Gate 4: named human's explicit approval. Automated tests cannot grant this.

## Rollback and residual risks

Describe recovery, unsupported cases and decisions that remain with the owner.
