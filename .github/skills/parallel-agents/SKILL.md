---
name: parallel-agents
description: Coordinate independent workstreams and synthesize findings in a single-agent Copilot workflow.
---

# Overview

This skill adapts parallel-work reasoning for GitHub Copilot by splitting complex tasks into independent tracks and merging results without multi-agent orchestration.

# When to Use

- Use this skill when a task can be decomposed into independent tracks like security, performance, and testing.
- Use this skill when you need one prioritized synthesis instead of fragmented findings.

# Instructions

1. Define workstreams: Split the task into independent analysis or implementation tracks.
2. Execute each stream: Gather evidence and proposed changes per track.
3. Synthesize findings: Merge outputs into one ranked action list.
4. Implement by priority: Fix critical issues first, then important improvements.
5. Verify and report: Validate outcomes and summarize remaining risks.

# Best Practices

- Keep changes minimal, clear, and aligned with existing architecture.
- Validate assumptions with reproducible evidence before editing code.
- Add or update tests for behavior changes and regression prevention.
- Document trade-offs when multiple implementation approaches exist.

# Examples

- Use the parallel-agents skill to handle this task end-to-end.
- Apply parallel-agents to diagnose and fix the current issue.
- Use parallel-agents to propose a safe implementation plan and execute it.
