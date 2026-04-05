---
description: Preview/run guidance for local validation.
---

# Preview

$ARGUMENTS

Use this prompt to prepare local preview/run checks.

## Actions

- Determine how to run the app in this repository.
- Confirm required services (for example MySQL/XAMPP) are up.
- Start or verify local server command.
- Report URL and basic health checks.

## Output Template

## Preview Status
- Run command: <command>
- Expected URL: <url>
- Dependencies/services: <status>
- Health result: <pass/fail + note>

If blocked, provide exact blocker and minimal fix steps.
