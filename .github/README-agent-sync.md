# Agent Kit Sync Notes

This workspace now includes an adapted Copilot/Codex kit under `.github`.

## Synced Components

- prompts: `.github/prompts/`
- skills: `.github/skills/`
- agents: `.github/agents/`
- rules: `.github/rules/`
- scripts: `.github/scripts/`
- workflows (source markdown): `.github/workflows-md/`
- shared assets: `.github/.shared/ui-ux-pro-max/`
- mcp config: `.github/mcp_config.json`
- mcp template: `.github/mcp_config.template.json`

## Recommended Usage

1. Use prompt files in `.github/prompts/` for Copilot chat workflows.
2. Use `.github/rules/CODEX.md` as Codex operational guidance.
3. If MCP is needed, copy `.github/mcp_config.template.json` to your MCP runtime location and fill API keys.

## Parity Validation

- Quick parity check:
	- `python .github/scripts/parity_check.py`
- Strict parity check (fails if `.github` has any extra files too):
	- `python .github/scripts/parity_check.py --strict-extra`
