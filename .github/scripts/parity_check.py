#!/usr/bin/env python3
"""Parity checker for agent vs .github.

Usage:
    python .github/scripts/parity_check.py
    python .github/scripts/parity_check.py --strict-extra
"""

from __future__ import annotations

import argparse
import fnmatch
from pathlib import Path

DEFAULT_IGNORE = [
    "**/__pycache__/**",
    "**/*.pyc",
]


def list_files(root: Path, ignore_patterns: list[str]) -> set[str]:
    files: set[str] = set()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if any(fnmatch.fnmatch(rel, pattern) for pattern in ignore_patterns):
            continue
        files.add(rel)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Check file parity between agent and .github")
    parser.add_argument("--strict-extra", action="store_true", help="Fail if .github has extra files")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    agent_root = project_root / "agent"
    github_root = project_root / ".github"

    if not agent_root.exists() or not github_root.exists():
        print("ERROR: expected both 'agent' and '.github' folders.")
        return 2

    agent_files = list_files(agent_root, DEFAULT_IGNORE)
    github_files = list_files(github_root, DEFAULT_IGNORE)

    missing_in_github = sorted(agent_files - github_files)
    extra_in_github = sorted(github_files - agent_files)

    print(f"MISSING_IN_GITHUB_COUNT={len(missing_in_github)}")
    for item in missing_in_github:
        print(item)

    print(f"EXTRA_IN_GITHUB_COUNT={len(extra_in_github)}")
    for item in extra_in_github:
        print(item)

    if missing_in_github:
        return 1
    if args.strict_extra and extra_in_github:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
