# Review and evidence

## Scope and provenance

This is the finite template described in `spec.md`, not an application.
Claude Code 2.1.303, resolved model `claude-opus-5-5`, effort `max`, ultracode on,
fast off, supplied the strict schema validator. Its completed response explicitly
said it had not executed the code. Native orchestration integrated the loader,
runner, report writer, CLI, tests and documentation, and executed all checks.
No model-generated code is accepted merely because it was generated.

The broader Claude design/implementation attempts did not yield a completed
artifact. A narrowly scoped validator request did. Do not attribute the entire
project or local test execution to Claude. A subsequent external source critique
was blocked before a completed result; no Claude critique is claimed here.

## Concrete independent review defects fixed

1. A report target such as `.git/HEAD` was not tracked by Git and could pass the
   original tracked-file check. Independent review reproduced corruption in a
   disposable repository. The fix protects `.git`, Git's actual metadata
   directory and common directory, including linked worktrees. Regression tests
   cover metadata targets and confirm the disposable repository remains valid.
2. An unpaired Unicode surrogate in argv passed schema validation but failed
   during process encoding. Validation now rejects surrogate code points before
   any subprocess executes. A regression test verifies no command is started.

3. A follow-up review reproduced a metadata bypass when a repository parent
   path contained a newline. Git directory paths are now queried individually
   and only the terminating newline is removed. A real linked-worktree
   regression covers the newline-containing parent path.

Other adversarial coverage includes huge integer/NaN/infinite timeouts, nested
JSON duplicates, excess nesting, malformed UTF-8, oversized input, literal shell
metacharacters, late-invalid gate fail-before-run, fail-fast side-effect
prevention, and atomic write failure preserving the previous report.

## Verification

Run from the repository root:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/verify.py --config verification.json
python3 scripts/check_scope.py
```

The first post-fix run executed 22 tests with exit 0. Final-run evidence is
recorded in `docs/RESULTS.md`. The sample harness runs deterministic and
adversarial test subsets separately, followed by the syntax/LOC check. A green
third command is not a model simplification judgment or human approval.

## Debloating review

The starter uses functions and standard-library modules, with no dependency
framework, wrapper hierarchy, plugin mechanism or command denylist. Removed two
unused test imports. Production code grew during concrete safety fixes rather
than being artificially shrunk. No 20–30% reduction is claimed. Removing the
metadata check or Unicode validation to meet a quota would be a regression.

## Residual limitations

- No sandbox, no network isolation, no descendant-process containment guarantee.
- Report protection is best-effort and not race-proof against a hostile local
  process. Configured commands are explicitly trusted and can mutate any file.
- Existing reports can be stale; report authenticity is not cryptographically
  verified. Concurrent writers must choose distinct paths.
- Tested on Linux with Python 3.12.14. Windows/macOS execution has not been tested.
- The original active settings contain a machine-specific Windows guard path.
  They remain unchanged. No hook was replaced, bypassed or activated by this work.
- No package installation, GitHub push, merge or deployment was performed.
- Human approval remains pending. Passing commands do not certify zero defects.
