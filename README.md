# Sage MyPy Category Plugin

A MyPy plugin that enables proper `@override` checking for Sage's dynamic category method system.

## Overview

This plugin addresses the issue where MyPy's `@override` checker (from `typing.override`) fails to work correctly with Sage's dynamically constructed class hierarchy. In Sage, method containers like `ParentMethods`, `ElementMethods`, etc., are dynamically generated based on category relationships, but MyPy only sees the static source definitions.

The plugin works by intercepting MyPy's class MRO calculation and splicing in the appropriate ancestor method containers as static bases, allowing MyPy's `@override` checking to function properly.

## Installation

### From Source

```bash
# Clone the repository
git clone <repository-url>
cd sage-mypy-plugin

# Install in development mode
pip install -e .
```

### Using Sage's Python

If you're working within a Sage environment:

```bash
sage -pip install -e .
```

## Usage

To enable the plugin, add it to your MyPy configuration:

### Global Configuration (`~/.mypy.ini`)

```ini
[mypy]
plugins = sage_mypy_category_plugin.plugin
ignore_missing_imports = True
```

### Per-Project Configuration (`mypy.ini` or `setup.cfg`)

```ini
[mypy]
plugins = sage_mypy_category_plugin.plugin
ignore_missing_imports = True
```

### Command Line

```bash
mypy --plugin=sage_mypy_category_plugin.plugin your_file.py
```

### Bundled Sage interop stubs

The distribution bundles a narrow PEP 561 stub-only payload under
`sage-stubs`, so installing the package also installs the Sage interop stubs
for MyPy automatically. No separate `MYPYPATH` setup is required after
installation.

The bundled stubs intentionally stay small and only cover the Sage interfaces
this project consumes directly, such as:

- `sage.categories.category`
- `sage.categories.category_with_axiom`
- `sage.categories.homsets`
- `sage.misc.abstract_method`
- `sage.misc.cachefunc`
- `sage.misc.lazy_import`
- `sage.structure.category_object`
- `sage.structure.parent`
- `sage.sets.condition_set`

When working directly from a source checkout without installing the package,
make sure the repository root is on MyPy's package search path (for example by
putting the repo on `PYTHONPATH`) so MyPy can see the top-level `sage-stubs/`
directory.

## Configuration Options

The plugin can be configured via the `[sage-mypy-category-plugin]` section in your MyPy config file:

```ini
[sage-mypy-category-plugin]
strict = false
representative.MyCategory = SomeRepresentative, AnotherRepresentative
```

- `strict`: When enabled, the plugin will report errors for unresolved projections and missing type information (default: false)
- `representative.*`: Configure category representatives for parameterized categories

## How It Works

The plugin implements a `get_customize_class_mro_hook` that:

1. Identifies Sage category method containers (classes ending in `ParentMethods`, `ElementMethods`, etc.)
2. Uses Sage's introspection API to determine the correct static base classes for these method containers
3. Splices these base classes into the MRO (Method Resolution Order) before the final `object` entry
4. This allows MyPy's `@override` checker to walk the correct inheritance chain

## Development

### Running Tests

```bash
# Using justfile
just test

# Or directly with pytest
python -m pytest
```

### Building

```bash
python -m build
```

## Requirements

- Python >= 3.10
- MyPy >= 1.0
- SageMath (for the introspection components)

## License

This project does not currently specify a license. Please check with the maintainers for licensing information before use.

## Acknowledgments

This plugin was developed to support MyPy type checking in SageMath development environments, particularly for verifying `@override` annotations in category method containers.
