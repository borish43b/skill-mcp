---
name: code-review
description: Systematic code review checklist covering correctness, security, simplicity, and tests.
---

# Code Review

Systematic code review checklist. Apply in order.

## 1. Correctness
- Does the code do what the spec/task asks, nothing more?
- Check edge cases: empty inputs, boundaries, concurrency, failure paths.
- Verify error handling: are exceptions caught at the right level, not swallowed?

## 2. Security
- No injection (SQL, shell, path traversal, command).
- Secrets never hardcoded or logged.
- Untrusted input validated at the boundary.

## 3. Simplicity
- Is there a shorter, obvious version? Prefer boring over clever.
- Dead code, unused imports, and debug leftovers must go.

## 4. Tests
- Does a failing test exist for the reported bug?
- New behavior: is it covered by the narrowest meaningful test?
- Tests must be deterministic and isolated.

## Output format
Report findings as: file:line — problem — suggested fix.
Severity: critical / major / minor / nit.
