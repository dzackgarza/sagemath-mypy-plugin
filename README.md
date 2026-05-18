# Sage MyPy Category Plugin

This branch is an invariant-core rewrite. The legacy implementation, tests,
stubs, package metadata, and command runner were intentionally removed before
new code is accepted.

The current target is not consumer error-count reduction. The target is the
structural invariant in [.serena/plans/invariant-core-rewrite.md](.serena/plans/invariant-core-rewrite.md):

```text
mypy TypeInfo MRO
==
Sage runtime named-class MRO projected back to provider classes
```

Sage runtime is the semantic oracle. The mypy plugin may teach mypy recorded
provider inheritance facts; it must not reimplement Sage category semantics,
filter diagnostics, or add fallback behavior that makes a fixture pass without
the structural invariant.

Canonical local guidance:

- [AGENTS.md](AGENTS.md) defines repository rules, banned patterns, and the
  required behavioral test matrix.
- [GOALS.md](GOALS.md) records the historical scope and the reason suppression
  is not a permanent solution.
- [.serena/plans/invariant-core-rewrite.md](.serena/plans/invariant-core-rewrite.md)
  is the active rewrite plan.

There is no supported install or usage path on this branch until the rewrite
reintroduces package metadata, a justfile, and passing invariant-core tests.
