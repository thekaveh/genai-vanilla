---
name: audit
description: Audit local git changes before implementation or cleanup, including staged, unstaged, and untracked files. Use when asked to review uncommitted work, inspect local changes, find risks, or produce findings before applying fixes.
---

# Audit Uncommitted Changes

1. Run `git status --short --untracked-files=all` to inventory staged, unstaged, and untracked files.
2. Inspect diffs with `git diff --cached` and `git diff`.
3. For untracked paths, list files with `git ls-files --others --exclude-standard` and read each relevant file directly because `git diff` will not include them.
4. Read each changed file in full when needed to understand context.
5. Check against project conventions in the existing codebase.
6. Present a numbered list of all findings with severity before making changes.
7. Wait for user approval before making any changes.
8. Fix only approved items, one at a time, verifying no regressions.
