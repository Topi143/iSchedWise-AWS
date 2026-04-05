# Agent vs .github Parity Report

Date: 2026-03-17

## Result Summary

- Missing from `.github` compared to `agent`: 2 files
- Extra in `.github` compared to `agent`: 40 files

## Missing Files (Residual)

These are cache artifacts from the source and are intentionally excluded from `.github`:

1. `.shared/ui-ux-pro-max/scripts/__pycache__/core.cpython-313.pyc`
2. `.shared/ui-ux-pro-max/scripts/__pycache__/design_system.cpython-313.pyc`

## Extra Files in `.github` (Intentional Enhancements)

### Copilot/Codex integration
- `copilot-instructions.md`
- `rules/CODEX.md`
- `mcp_config.template.json`
- `README-agent-sync.md`

### Prompt workflows (native Copilot)
- `prompts/*.prompt.md` (11 files)
- `prompts/README.md`

### Skill normalization/expansion
- Top-level game skill mirrors:
  - `skills/2d-games/SKILL.md`
  - `skills/3d-games/SKILL.md`
  - `skills/game-art/SKILL.md`
  - `skills/game-audio/SKILL.md`
  - `skills/game-design/SKILL.md`
  - `skills/mobile-games/SKILL.md`
  - `skills/multiplayer/SKILL.md`
  - `skills/pc-games/SKILL.md`
  - `skills/vr-ar/SKILL.md`
  - `skills/web-games/SKILL.md`
- Additional adapted skill entries:
  - `skills/frontend-design/SKILL.md`
  - `skills/react-best-practices/SKILL.md`
  - `skills/templates/SKILL.md`

### Workflow markdown mirror folder
- `workflows-md/*.md` (11 files)

## Sync Actions Performed

1. Copied all missing files from `agent` to `.github` by relative path.
2. Synced `agents`, `rules`, `scripts`, `workflows`, and `.shared` assets.
3. Normalized references from `.agent` paths to `.github` paths.
4. Removed cache artifacts (`__pycache__`, `.pyc`) from `.github`.
5. Fixed accidental nested script folders:
   - `skills/frontend-design/scripts/scripts` -> flattened
   - `skills/nextjs-react-expert/scripts/scripts` -> flattened

## Validation

- Python syntax compile passed:
  - `.github/scripts/*.py`
  - `.github/.shared/ui-ux-pro-max/scripts/*.py`
- No `.agent/` path references remain under `.github`.

## Recommendation

Current state is production-ready for your `.github`-based Copilot/Codex setup. Keep `.pyc` files excluded.
