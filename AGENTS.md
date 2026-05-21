# AGENTS.md — sage-mypy-category-plugin

## Purpose

Sage's category system dynamically injects methods into classes at runtime.
Mypy only sees static source definitions, so it cannot walk the real MRO for
method containers like `ParentMethods`, `ElementMethods`, `MorphismMethods`,
and `SubcategoryMethods`. This means `@override` decorators on methods in
those containers always fire false-positive "no base method was found" errors
— even when the override is completely correct.

This plugin's sole job is to fix that: given a method container, determine its
true Sage semantic base containers at analysis time and splice them into mypy's
MRO so that `@override` checking produces correct results.

The primary consumer is `category_specs/` in the research repo — a package
that defines its own local wrapper base classes (not direct `sage.categories.*`
subclasses). The plugin must work for that namespace. Passing only against
`sage.categories.*` fixtures is not sufficient.

---

## Banned Patterns

### Hardcoded namespace prefixes in resolution logic

**Never** write namespace filters of the form:

```python
idx = fullname.find("sage.categories.")
if idx > 0:
    fullname = fullname[idx:]
```

or any equivalent guard that strips, skips, or short-circuits based on a
literal module prefix string (`"sage."`, `"sage.categories."`, etc.).

**Why it is banned:** The plugin is explicitly required to handle third-party
namespaces (e.g. `category_specs.*`) that do not live under `sage.categories`.
A hardcoded prefix check silently makes the plugin a no-op for every consumer
outside that prefix. The hook fires (`_looks_like_method_container` matches on
the `Methods` suffix), returns `None`, and mypy sees no MRO injection — so
every `@override` in the target namespace fires a false-positive "no base
method was found" error.

This pattern was present in `_resolve_direct_bases` at the time this rule was
written. It made the plugin's own integration tests green (all fixtures used
`sage.categories.*` or direct-Sage-subclassing third-party categories) while
the actual consumer (`category_specs.*` using local wrapper base classes)
produced 359 uncaught `[misc]` override errors.

**Fix:** Resolution logic must be namespace-agnostic. Use
`parse_method_container_fullname` (which is already documented as
namespace-agnostic) and validate via runtime introspection, not prefix
matching. If introspection fails for a namespace, fail loudly in strict mode
rather than silently returning `None`.

---

### Fixtures that inherit from `sage.categories.category.Category` directly

Third-party namespace fixtures **must not** inherit from
`sage.categories.category.Category` (or any other `sage.*` base) directly.

**Why it is banned:** The introspection path uses `issubclass(obj, Category)`
to locate category objects in a module and then calls Sage's runtime to resolve
their super-categories. A fixture that inherits directly from Sage's `Category`
is resolvable by the introspection layer even when the plugin's namespace
handling is completely broken for the real consumer.

This is exactly the fraud that was present: `test_third_party_*` tests passed
because every `third_party_pkg` fixture used `from sage.categories.category
import Category` as its base — so Sage's runtime could walk the hierarchy
regardless of any namespace-prefix bug. The tests appeared to validate
namespace-agnostic behavior while proving nothing of the kind.

**Fix:** Third-party fixtures must inherit from a **local wrapper base** that
itself inherits from Sage, mirroring the `category_specs` pattern:

```python
# correct fixture structure
from sage.categories.category_singleton import Category_singleton as _SageBase

class LocalCategoryBase(_SageBase):   # local wrapper, not direct Sage import
    ...

class FixtureCategory(LocalCategoryBase):
    class ParentMethods:
        def f(self) -> int: ...

class FixtureSubCategory(LocalCategoryBase):
    class ParentMethods:
        @override
        def f(self) -> int: ...        # must resolve through the local wrapper
```

---

### Silent exception swallowing in projection paths

`_resolve_projection` catches `Exception` broadly and returns `None` in
non-strict mode. This is acceptable as a last resort, but every caught
exception must be logged at DEBUG level so failures are diagnosable without
enabling strict mode. Silently returning `None` from a projection that crashes
on a `ModuleNotFoundError` (as observed for `category_specs.*` introspection)
is indistinguishable from "this class needs no MRO injection."

---

## Testing

**Before writing any test, load and read the `test-guidelines` skill
(`~/.claude/skills/test-guidelines/`). It is the authoritative standard.
The plugin-specific rules below are elaborations of that standard, not
replacements for it.**

### Owned surface

The plugin's only owned surface is **mypy exit code and error output given a
fixture file**. Every test runs mypy and asserts on that. Internal unit tests
of introspection helpers, alias resolution, or module imports are not plugin
tests and do not substitute for them.

### Conjunction pattern

Every behavioral surface is fully characterised by the conjunction of
**(plugin on/off) × (valid/invalid usage)**. Each surface must have exactly
one test that asserts all cases simultaneously. A test that passes before the
fix is not a TDD test.

For an `@override` surface:

| plugin | usage   | expected                                 |
|--------|---------|------------------------------------------|
| on     | valid   | exit 0                                   |
| on     | invalid | exit nonzero, "no base method was found" |
| off    | valid   | exit nonzero, "no base method was found" |
| off    | invalid | exit nonzero, "no base method was found" |

For a surface that suppresses a specific error code (e.g. `[attr-defined]`,
`[assignment]`):

| plugin | expected                      |
|--------|-------------------------------|
| on     | exit 0                        |
| off    | exit nonzero, `[error-code]`  |

See the `category_specs_like` fixtures and behavior-matrix tests for the
reference implementation.

### Validity requirement: plugin=off must produce an error

Every conjunction test must verify that the error the plugin is meant to suppress
actually appears when the plugin is disabled. If `plugin=off` produces exit 0 for
a fixture, the fixture is not testing the plugin — it is testing that mypy passes
code the plugin has no role in. Such a fixture proves nothing and must be rewritten
until the `plugin=off` case produces the expected error.

This is the same principle as the Iron Law of TDD: a test that passes before the
fix is not a test of the fix.

### Fixture inheritance

Fixtures for namespace-agnostic tests must inherit from a **local wrapper
base** (defined in `tests/fixtures/local_wrapper_pkg/`), not from
`sage.categories.category.Category` directly. A fixture that inherits from
Sage directly is resolvable by Sage's runtime introspection even when the
plugin's namespace handling is completely broken — making the test a false
green. See the Banned Patterns section above for the full explanation.
