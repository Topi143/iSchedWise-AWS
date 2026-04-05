---
description: Systematic debugging workflow with root cause and prevention.
---

# Debug

$ARGUMENTS

Use this prompt to investigate and fix bugs.

## Steps

1. Capture symptom, expected behavior, and reproduction.
2. List likely hypotheses ordered by probability.
3. Validate each hypothesis with evidence.
4. Identify root cause.
5. Apply minimal safe fix.
6. Add prevention (validation, test, guard clause, logging).

## Output Template

## Debug: <issue>

### Symptom
<what fails>

### Evidence
- Error: <message>
- Location: <file + line>
- Repro: <steps>

### Hypotheses
1. <cause>
2. <cause>
3. <cause>

### Investigation
- Hypothesis 1: <check> -> <result>
- Hypothesis 2: <check> -> <result>

### Root Cause
<why it happened>

### Fix
<what changed and why>

### Prevention
<tests/guards added>
