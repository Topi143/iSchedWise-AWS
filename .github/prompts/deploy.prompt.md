---
description: Deployment readiness and safe release checklist for this project.
---

# Deploy

$ARGUMENTS

Use this prompt for release checks and deployment guidance.

## Pre-Deployment Checklist

- App starts locally without errors.
- Python dependencies installed and pinned.
- Critical routes return expected status.
- DB migrations/schema changes validated.
- No secrets committed.
- Key flows tested: login, role access, evaluation submission.
- Rollback plan documented (DB backup + previous commit/tag).

## Output Template

## Deployment Plan

### Environment
<dev/staging/prod>

### Checks
- Code quality: <pass/fail>
- Security: <pass/fail>
- Performance sanity: <pass/fail>

### Release Steps
1. <step>
2. <step>
3. <step>

### Verification
- Health endpoint/page: <result>
- Database connectivity: <result>
- Core user flows: <result>

### Rollback
<exact rollback action>
