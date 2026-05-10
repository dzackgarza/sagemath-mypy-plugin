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
