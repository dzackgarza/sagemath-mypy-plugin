from __future__ import annotations

from pathlib import Path
from sys import argv

CONFIG_TEMPLATE = """[mypy]
plugins = sage_mypy_category_plugin.plugin
ignore_missing_imports = True
explicit_package_bases = True

[sage-mypy-category-plugin]
packages =
    category_specs
roles =
    parent
    element
    subcategory
    morphism
    homset_parent
    homset_element
cache_dir = {cache_dir}
"""

DEBUG_TEMPLATE = """[mypy]
plugins = sage_mypy_category_plugin.plugin
ignore_missing_imports = True
explicit_package_bases = True

[sage-mypy-category-plugin]
manifest = {manifest}
"""


def main() -> None:
    if len(argv) < 2:
        raise SystemExit("usage: write_consumer_config CONFIG_FILE [MANIFEST_PATH]")
    config_file = Path(argv[1])
    manifest = argv[2] if len(argv) > 2 else ""
    cache_dir = argv[3] if len(argv) > 3 else ""
    if manifest:
        config_file.write_text(DEBUG_TEMPLATE.format(manifest=manifest))
    else:
        config_file.write_text(CONFIG_TEMPLATE.format(cache_dir=cache_dir))


if __name__ == "__main__":
    main()
