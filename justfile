set shell := ["bash", "-uc"]

@default:
  just --list

@test *args:
  sage -python -m pytest --ignore=tests/fixtures {{args}}

@mypy-fixture fixture config="tests/mypy_test.ini":
  #!/usr/bin/env bash
  set -euo pipefail
  export PYTHONPATH="tests/fixtures${PYTHONPATH:+:$PYTHONPATH}"
  sage -python -m mypy --config-file {{config}} --no-incremental tests/fixtures/sage/categories/mypy_test_fixtures/{{fixture}}.py

@consumer-mypy:
  #!/usr/bin/env bash
  set -euo pipefail
  export PYTHONPATH="{{justfile_directory()}}${PYTHONPATH:+:$PYTHONPATH}"
  cd /home/dzack/research
  sage -python -m mypy \
    --config-file /home/dzack/ai/quality-control/mypy-global.ini \
    --ignore-missing-imports \
    --explicit-package-bases \
    category_specs/homsets/homsets.py \
    category_specs/homsets/endsets.py \
    category_specs/homsets/autsets.py \
    category_specs/sets/homsets.py \
    category_specs/topological_spaces/homsets.py
