---
name: git-workflow
description: Conventions for branching, committing, and merging in this repository.
---

# Git Workflow

Conventions for committing and branching in this repository.

## Branching
- Branch names: `fix/<short-summary>`, `feat/<short-summary>`, `chore/<short-summary>`.
- Branch off `main`, keep it small, delete after merge.

## Commits
- One logical change per commit; imperative subject ≤ 72 chars.
- Body explains *why*, not *what*.
- Never commit secrets, build artifacts, or local config.

## Merging
- Rebase onto `main` before requesting review.
- Squash PR branches to a single clean commit.
- `main` is always deployable; protect it with CI.
