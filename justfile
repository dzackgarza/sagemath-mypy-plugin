set shell := ["bash", "-uc"]
set quiet := true

@default:
    just --list

@test *args:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -n "{{ args }}" ]; then
      sage -python -m pytest --ignore=tests/fixtures {{ args }}
      exit 0
    fi

    pids=()

    run_group() {
      sage -python -m pytest -q --ignore=tests/fixtures "$@" &
      pids+=("$!")
    }

    run_group tests/test_debug_oracle.py
    run_group tests/test_local_wrapper_namespace.py
    run_group tests/test_mypy_integration.py -k 'not incremental_determinism and not ancestor_change_reactivity and not parameterized_configured and not strict and not unresolved and not base_unmapped and not typeinfo_missing'
    run_group tests/test_mypy_integration.py::test_incremental_determinism
    run_group tests/test_mypy_integration.py::test_ancestor_change_reactivity
    run_group \
      tests/test_mypy_integration.py::test_parameterized_configured \
      tests/test_mypy_integration.py::test_parameterized_strict_without_config_reports_diagnostic \
      tests/test_mypy_integration.py::test_unresolved_strict_reports_diagnostic \
      tests/test_mypy_integration.py::test_base_unmapped_strict_reports_diagnostic \
      tests/test_mypy_integration.py::test_typeinfo_missing_strict_reports_diagnostic

    status=0
    for pid in "${pids[@]}"; do
      if ! wait "$pid"; then
        status=1
      fi
    done
    exit "$status"

@mypy-fixture fixture config="tests/mypy_test.ini":
    #!/usr/bin/env bash
    set -euo pipefail
    export PYTHONPATH="tests/fixtures${PYTHONPATH:+:$PYTHONPATH}"
    sage -python -m mypy --config-file {{ config }} --no-incremental tests/fixtures/sage/categories/mypy_test_fixtures/{{ fixture }}.py

@consumer-mypy:
    #!/usr/bin/env bash
    set -euo pipefail
    export PYTHONPATH="{{ justfile_directory() }}${PYTHONPATH:+:$PYTHONPATH}"
    cd /home/dzack/research
    sage -python -m mypy \
      --config-file /home/dzack/ai/quality-control/mypy-global.ini \
      --no-incremental \
      --ignore-missing-imports \
      --explicit-package-bases \
      category_specs/homsets/homsets.py \
      category_specs/homsets/endsets.py \
      category_specs/homsets/autsets.py \
      category_specs/sets/homsets.py \
      category_specs/topological_spaces/homsets.py
