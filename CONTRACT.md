# CONTRACT.md — sage-mypy-category-plugin

Non-negotiable invariants and banned patterns. Every change to the plugin,
resolver, oracle, stubs, fixtures, or tests must respect this contract.

## Invariants

### I1. Sage Runtime Is The Oracle

The plugin does not infer Sage category semantics from source syntax.
Every provider projection traces to `Category._make_named_class` or an
approved dynamic class construction. No AST parsing, no regex on `class`
definitions, no encoding of Sage category hierarchy rules in plugin code.

### I2. No Diagnostic Filtering

The plugin does not remove, suppress, or silence mypy error codes.
It teaches mypy the truth (via MRO projection, stub generation, or future
hook mechanisms) so that mypy's own rules reach correct conclusions.
Suppression documented in GOALS.md is explicitly a stopgap that must be
replaced by a teaching implementation.

### I3. No Namespace Hardcoding

The plugin does not hardcode consumer package names ("category_specs"),
class names, module prefixes ("sage.categories."), or any string that
ties resolution logic to a specific namespace. Resolution must use
runtime introspection (`issubclass`, Sage APIs, oracle tracing), not
string matching. The `parse_method_container_fullname` helper is
namespace-agnostic by design.

### I4. No Silent Fallbacks In Strict Mode

In strict mode, the plugin must not silently fall back to:

- `builtins.object`
- `Any`
- Empty provider bases / empty MRO
- No-op (returning `None` from a hook while swallowing the error)
- Baseline mypy behavior without an explicit error

Any projection failure in strict mode must produce a `CompileError` or
`ctx.api.fail(...)` so the user sees the failure immediately.

### I5. Structural MRO Invariant

For every projected provider P:

```
mypy TypeInfo.mro(P)
  ==
project_provider_classes(SageRuntimeNamedClass(P).__mro__) + builtins.object
```

and:

```
mypy TypeInfo.bases(P)
  ==
project_provider_bases(SageRuntimeNamedClass(P).__bases__)
```

A behavior test that passes without this structural invariant is
not proof.

### I6. Behavior Test Conjunction Matrix

Every behavior surface is characterised by the conjunction of
**(plugin on/off) × (valid/invalid usage)**. Each surface must have
exactly one test that asserts all cases simultaneously:

| plugin | usage   | expected                                   |
|--------|---------|--------------------------------------------|
| on     | valid   | exit 0, no errors                          |
| on     | invalid | exit nonzero, standard mypy error          |
| off    | valid   | exit nonzero, "no base method was found"   |
| off    | invalid | exit nonzero, "no base method was found"   |

Plugin-on-only success tests are forbidden.
Tests where `plugin=off` produces exit 0 are not testing the plugin.

### I7. Fixture Inheritance Integrity

Third-party namespace fixtures must inherit from a **local wrapper base**
that itself inherits from Sage, not from `sage.categories.category.Category`
directly. A fixture that inherits from Sage directly is resolvable by
Sage's runtime introspection even when the plugin's namespace handling
is completely broken — making the test a false green.

## Banned Patterns

### BP1. Hardcoded namespace prefixes in resolution logic

```python
# BANNED
idx = fullname.find("sage.categories.")
if idx > 0:
    fullname = fullname[idx:]
```

Any guard that strips, skips, or short-circuits based on a literal module
prefix string is forbidden. Use runtime introspection instead.

### BP2. Fixtures that inherit from sage.categories.category.Category directly

```python
# BANNED for third-party namespace tests
from sage.categories.category import Category
class MyCategory(Category): ...
# Correct:
from sage.categories.category_singleton import Category_singleton as _SageBase
class LocalCategoryBase(_SageBase): ...
class MyCategory(LocalCategoryBase): ...
```

### BP3. Silent exception swallowing in projection paths

```python
# BANNED
try:
    return _resolve_projection(...)
except Exception:
    return None  # indistinguishable from "no projection needed"
```

Every caught exception must be logged at DEBUG level in non-strict mode
so failures are diagnosable. In strict mode, exceptions must propagate or
produce `CompileError`/`ctx.api.fail(...)`.

### BP4. Changing expected errors to match current behavior

Tests must assert the correct behavior. If the plugin's behavior changes,
the test must reflect the desired new behavior — not the accidental
current behavior. Adjusting expected errors downward without a correctness
argument is banned.

### BP5. Consumer-driven patching

Consumer failures (`category_specs`) must first become small oracle-backed
structural tests in the repo. Do not edit consumer code to work around
plugin limitations. Do not fix consumer error counts as a proxy for plugin
correctness.

### BP6. Testing mock behavior instead of real behavior

Tests that mock Sage runtime internals or `Category._make_named_class`
without actually exercising the real Sage runtime are not valid.
Use real Sage categories with real `super_categories()`, real provider
classes, real category inheritance, and real method declarations.

### BP7. Adding broad hooks to patch call sites

The plugin's core must remain limited to:
- `get_customize_class_mro_hook`
- `get_additional_deps`
- `report_config_data`

New hooks (`get_function_hook`, `get_method_hook`, `get_attribute_hook`,
`get_base_class_hook`) may only be added with explicit justification in
the Suppression Registry and a linked structural test.

### BP8. Requiring external generation steps

The plugin must own its manifest generation lifecycle. Users must
not be required to:
- Run `just generate-manifest` before `sage -python -m mypy`
- Use an external wrapper script
- Set `MYPYPATH` via environment variable or external tooling
- Declare `cache_dir/stubs` in `mypy_path` so normal plugin execution can see
  generated upstream Sage provider stubs

**Upstream Sage visibility comes from the Sage-version sidecar stubs.** Under
mypy 2.0.x (compiled via mypyc), `compute_search_paths()` runs before
`load_plugins()`, so plugin `__init__` runs after search paths are already
frozen. Normal production execution therefore must not rely on upstream Sage
provider stubs generated into `cache_dir/stubs` during plugin initialization.
Those provider modules must be supplied by the installed `sage-stubs` sidecar
or by real source visible to mypy.

The correct config pattern is:

```ini
[mypy]
plugins = sage_mypy_category_plugin.plugin

[sage-mypy-category-plugin]
packages = my_category_package
cache_dir = .mypy_cache/sage-category-plugin
```

The plugin still owns projection generation: it produces or refreshes the
manifest during `__init__` on first run. No manual generation, no wrapper, no
environment variable, and no cache-stub `mypy_path` entry are part of the
production contract. Debug manifest/runtime-alias paths must be documented as
non-production and may not be counted as release acceptance evidence.

### BP9. Using Any/object/empty provider bases as a success path

Any use of `Any`, `object`, empty MRO, or synthesized provider fallback
that makes a test pass without proving the structural invariant is banned.

### BP10. Marking failing real examples as xfail without a deletion condition

`@pytest.mark.xfail` may only be used with `strict=True` and with a
documented condition under which the xfail will be removed (specific test
addition, Sage version upgrade, mypy feature).

## Sentinel Checklist

Before promoting work to complete, verify these sentinel checks:

```text
grep for diagnostic filter functions:
  rg -n 'def _filter' sage_mypy_category_plugin/
  rg -n 'diagnostic' sage_mypy_category_plugin/
  Must produce only the registered suppression in GOALS.md.

grep for namespace strings:
  rg -n '"sage\.categories\.' sage_mypy_category_plugin/
  rg -n '"category_specs' sage_mypy_category_plugin/
  Must match only test-constant definitions in tests/, never in plugin code.

grep for silent fallbacks:
  rg -n 'except Exception' sage_mypy_category_plugin/
  rg -n 'return None$' sage_mypy_category_plugin/
  Each hit must have a documented reason.

grep for banned hooks:
  rg -n 'get_function_hook\|get_method_hook\|get_attribute_hook\|get_base_class_hook' sage_mypy_category_plugin/plugin.py
  Must be empty or justified in GOALS.md Suppression Registry.
```
