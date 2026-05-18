set shell := ["bash", "-uc"]

@default:
  just --list

@test *args:
  #!/usr/bin/env bash
  set -euo pipefail
  export PYTHONPATH="${PWD}${PYTHONPATH:+:${PYTHONPATH}}"
  args=({{args}})
  for arg in "${args[@]}"; do
    if [[ "$arg" != -* ]]; then
      sage -python -m pytest "${args[@]}"
      exit
    fi
  done

  output_dir="$(mktemp -d)"
  trap 'rm -rf "${output_dir}"' EXIT
  failures=0
  labels=(
    structural
    manifest
    plugin_projection
    resolver_cli
    stubs
    behavior
  )
  commands=(
    "tests/test_oracle_projection.py tests/test_homset_projection.py tests/test_provider_role_projection.py"
    "tests/test_manifest.py"
    "tests/test_plugin_projection.py"
    "tests/test_resolver_cli.py"
    "tests/test_stub_generation.py"
    "tests/test_behavior_matrix.py tests/test_role_behavior_matrix.py"
  )

  for index in "${!labels[@]}"; do
    label="${labels[$index]}"
    read -r -a files <<< "${commands[$index]}"
    (
      sage -python -m pytest "${files[@]}" "${args[@]}"
    ) >"${output_dir}/${label}.log" 2>&1 &
    printf '%s\n' "$!" >"${output_dir}/${label}.pid"
  done

  for label in "${labels[@]}"; do
    if ! wait "$(cat "${output_dir}/${label}.pid")"; then
      failures=1
    fi
  done

  for label in "${labels[@]}"; do
    printf '\n== %s ==\n' "$label"
    cat "${output_dir}/${label}.log"
  done

  exit "$failures"

[group('test')]
test-structural *args:
  just test tests/test_oracle_projection.py tests/test_homset_projection.py tests/test_provider_role_projection.py {{args}}

[group('test')]
test-manifest *args:
  just test tests/test_manifest.py {{args}}

[group('test')]
test-plugin-projection *args:
  just test tests/test_plugin_projection.py {{args}}

[group('test')]
test-resolver-cli *args:
  just test tests/test_resolver_cli.py {{args}}

[group('test')]
test-stubs *args:
  just test tests/test_stub_generation.py {{args}}

[group('test')]
test-behavior *args:
  just test tests/test_behavior_matrix.py tests/test_role_behavior_matrix.py {{args}}

[group('test')]
release-check:
  just test
