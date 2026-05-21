# sage-mypy-category-plugin

A mypy plugin that projects Sage category provider-class MROs into mypy's
TypeInfo graph, enabling standard mypy inheritance checks (`@override`,
`@final`, abstract methods, signature compatibility) on Sage category
provider classes.

## The problem

Sage builds its category hierarchy at runtime via `Category._make_named_class`.
When a category `C` is instantiated, Sage creates named classes
(`parent_class`, `element_class`, …) whose MROs are derived by C3 linearisation
of the corresponding inner classes (`ParentMethods`, `ElementMethods`, …) across
the full super-category chain. This MRO is not written in any source file;
mypy cannot see it. Without the plugin, every `@override` annotation on a
provider method fails with "no base method was found."

## How it works

At plugin initialisation, the plugin imports the configured category packages
under the Sage Python interpreter, introspects the live runtime MROs of every
provider named class, projects them back to source provider classes, and writes
a validated manifest. During the mypy analysis pass, `get_customize_class_mro_hook`
rewrites each provider's `TypeInfo.bases` and `TypeInfo.mro` to match the
manifest projection. Mypy's ordinary inheritance rules then apply correctly.

The formal correctness argument is in [SPEC.md](SPEC.md).
Non-negotiable invariants and banned patterns are in [CONTRACT.md](CONTRACT.md).

## Installation

The plugin requires Sage Python and a pinned mypy version. Install from source
in the Sage Python environment, together with the Sage-version sidecar stubs:

```bash
sage -python -m pip install -e .
sage -python -m pip install "git+https://github.com/dzackgarza/sage-stubs@c99550bc405620b9b8f25e1890f25dd88fecc241"
```

Verify that the installed mypy version matches the pinned version:

```bash
just test-supported-mypy
```

## Configuration

Add a `[sage-mypy-category-plugin]` section to your `mypy.ini` (or equivalent
config file):

```ini
[mypy]
plugins = sage_mypy_category_plugin.plugin

[sage-mypy-category-plugin]
packages =
    my_category_package
    another.category.package

roles =
    parent
    element
    subcategory
    morphism
    homset_parent
    homset_element

cache_dir = .mypy_cache/sage-category-plugin
strict = true
```

> **Why sidecar stubs?** Under mypy 2.0 (compiled via mypyc), mypy computes
> its module search paths before loading plugins. Upstream Sage provider
> visibility therefore comes from the installed Sage-version `sage-stubs`
> sidecar, not from stubs generated into the plugin cache during `plugin.__init__`.
> Normal production configs should not declare `cache_dir/stubs` on
> `mypy_path`.

### Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `packages` | yes | — | Python package names to scan for Sage category classes. The plugin imports each package under Sage Python at startup. |
| `roles` | no | `parent` | Provider roles to project. Available: `parent`, `element`, `subcategory`, `morphism`, `homset_parent`, `homset_element`. |
| `cache_dir` | no | `.mypy_cache/sage-category-plugin` | Directory for the generated projection manifest. Relative paths are resolved from the config file's directory. |
| `strict` | no | `false` | If `true`, any projection failure (missing TypeInfo, MRO mismatch) causes a hard mypy error instead of a warning. |

### Running mypy

```bash
sage -python -m mypy --config-file mypy.ini my_category_package
```

No external pre-generation step is required. The plugin generates and caches
the projection manifest during the first mypy run. Upstream Sage provider
classes must be visible through the installed Sage-version sidecar stubs.

## Cache lifecycle

The plugin caches the projection manifest in `cache_dir`:

```
cache_dir/
    projection-manifest.json  ← projection manifest (validated Pydantic model)
```

**What triggers regeneration:**

- The manifest is absent or unreadable.
- The Sage version in the manifest does not match the running Sage.
- The mypy version is outside the manifest's `[mypy_min_version, mypy_max_version]` range.
- The SHA-256 digest of any source module tracked in the manifest has changed.
- The `report_config_data` hook detects a manifest digest change (mypy's incremental-mode mechanism).

**What does not trigger regeneration:**

- Mypy incremental-mode `.mypy_cache` changes (mypy manages those separately).
- Changes to files outside the configured `packages`.

## Failure modes

| Failure | Symptom | Cause | Fix |
|---------|---------|-------|-----|
| Missing `[sage-mypy-category-plugin]` section | `CompileError: Missing section` | Config file does not have the plugin section | Add `[sage-mypy-category-plugin]` to `mypy.ini` |
| `packages` not specified | `CompileError: must specify 'packages'` | Config section is present but empty | Add `packages = ...` |
| Provider TypeInfo not found | `Sage category provider projection … references missing symbols` | A projected provider class is not visible to mypy (missing sidecar stub or source) | Ensure consumer `packages` are source roots/importable and the Sage-version `sage-stubs` sidecar is installed |
| MRO mismatch after projection | `Sage category provider MRO mismatch: expected … observed …` | TypeInfo lookup succeeded but mypy resolved a different order | Usually indicates a stale manifest; delete `cache_dir` and rerun |
| Sage runtime import error | `CompileError: ...` during plugin `__init__` | A package in `packages` cannot be imported under Sage Python | Verify the package is installed and importable: `sage -python -c "import my_package"` |
| Manifest validation error | `ValidationError: …` | The cached manifest is corrupted or was written by an incompatible plugin version | Delete `cache_dir` and rerun |

## Debugging

**Inspect the generated manifest:**

```bash
python -m json.tool .mypy_cache/sage-category-plugin/projection-manifest.json | head -100
```

**Generate an inspection manifest manually (CLI resolver):**

```bash
just generate-manifest \
    --package my_category_package \
    --roles parent element \
    --output .mypy_cache/sage-category-plugin/projection-manifest.json
```

The CLI resolver is for inspection and bisecting projection issues. It is not
part of the production mypy path; normal mypy runs generate and refresh their
own projection manifest from `packages`.

**Run only the behavior test matrix:**

```bash
just test-behavior
```

**Run the mutation proof suite:**

```bash
just test-mutation
```

## Sage and mypy version pinning

The plugin pins mypy at the version shipped with the Sage Python environment.
The manifest records the Sage version and git revision at generation time,
plus `mypy_min_version`/`mypy_max_version` bounds. Running with a different
mypy version triggers manifest regeneration (or a hard error if the new version
is outside the supported range).

To verify pinning:

```bash
just test-supported-mypy
```

## Development

```bash
just test            # run all test batches in parallel
just test-structural # oracle/projection/MRO tests only
just test-behavior   # behavior matrix (plugin on/off × valid/invalid)
just test-mutation   # mutation proof suite
just release-check   # performance gate + version pin + mutation suite
just typecheck       # mypy on the plugin source itself
```

## Design references

- [SPEC.md](SPEC.md) — formal correctness argument
- [CONTRACT.md](CONTRACT.md) — non-negotiable invariants and banned patterns
- [AGENTS.md](AGENTS.md) — repository rules for agents
- [GOALS.md](GOALS.md) — historical scope and suppression rationale
