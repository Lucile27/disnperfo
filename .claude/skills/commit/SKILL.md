---
name: commit
description: Use when the user wants to create a git commit and push. Writes a conventional commit message based on the staged diff.
---

Create a git commit and push it.

Steps:
1. Run `git status` to see staged and unstaged changes.
2. If nothing is staged, run `git add <relevant files>`.
3. Run `git diff --staged` to see exactly what will be committed.
4. Draft a conventional commit message:
   - Format: `<type>: <short description>`
   - Types: feat, fix, docs, refactor, test, chore, perf, style
   - Keep subject under 72 characters.
   - Add a body paragraph only if the change is non-trivial.
5. Run `git commit -m "<message>"`.
6. Run `git push origin <current-branch>`.
7. Report the commit hash and confirm the push succeeded.
