---
description: Generate or run tests with clear coverage and failure reporting.
---

# Test

$ARGUMENTS

Use this prompt to create tests, run tests, or analyze failures.

## Behavior

- If target file/feature is provided: propose and create focused tests.
- If no target is provided: run existing relevant tests and summarize results.
- Include edge cases and error handling paths.

## Output Template

## Test Report
- Target: <feature/file>
- Test type: <unit/integration/e2e>
- Cases covered: <list>
- Result: <pass/fail summary>
- Failures: <key assertions/errors>
- Next fix action: <single action>
