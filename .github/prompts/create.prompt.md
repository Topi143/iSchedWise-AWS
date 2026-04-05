---
description: Build a new feature/app flow with planning, implementation, and verification.
---

# Create

$ARGUMENTS

Use this prompt when user asks to create something new.

## Process

1. Extract requirements from the request.
2. If missing essentials, ask concise questions.
3. Propose a short implementation plan (files, APIs, UI, validation).
4. Implement in the current codebase using existing patterns.
5. Verify by running relevant checks/tests.
6. Summarize created files and next steps.

## IntellEvalPro Defaults

- Backend: Flask blueprints + MySQL
- Frontend: Jinja templates + Tailwind + Flowbite + jQuery
- API: Consistent JSON (`success`, `message`, `data`)
- Security: parameterized SQL, role decorators, input validation
- Responsive baseline: mobile-first from 390px

## Guardrails

- Reuse existing modules first.
- Avoid introducing new frameworks unless explicitly requested.
- Keep changes scoped and production-ready.
