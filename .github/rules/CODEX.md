# CODEX Rules for IntellEvalPro

This file adapts the agent-kit operating rules for Codex-style assistants.

## Core Behavior

1. Identify request type first: question, analysis, simple edit, complex implementation.
2. For complex requests, ask clarifying questions before coding.
3. Prefer smallest safe change set.
4. Verify changed behavior with relevant checks.
5. Report findings and residual risks clearly.

## Routing Guide

- UI/UX work: use guidance from `.github/agents/frontend-specialist.md` and `.github/skills/frontend-design`.
- Backend/API work: use `.github/agents/backend-specialist.md` and `.github/skills/api-patterns`.
- Data/schema work: use `.github/agents/database-architect.md` and `.github/skills/database-design`.
- Security review: use `.github/agents/security-auditor.md` and `.github/skills/vulnerability-scanner`.
- Debugging: use `.github/agents/debugger.md` and `.github/skills/systematic-debugging`.

## Validation Scripts

- Quick checks: `python .github/scripts/checklist.py .`
- Full checks: `python .github/scripts/verify_all.py . --url <URL>`
- Preview status: `python .github/scripts/auto_preview.py status`

## Path Convention

- Use `.github` as the source of truth for prompts, rules, scripts, skills, and shared assets.
- Do not reference `.agent` paths in new docs or scripts.
