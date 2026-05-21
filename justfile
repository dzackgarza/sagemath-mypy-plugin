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
    automation
  )
  commands=(
    "tests/test_oracle_projection.py tests/test_homset_projection.py tests/test_provider_role_projection.py tests/test_axiom_projection.py"
    "tests/test_manifest.py"
    "tests/test_plugin_projection.py"
    "tests/test_resolver_cli.py"
    "tests/test_stub_generation.py"
    "tests/test_behavior_matrix.py tests/test_role_behavior_matrix.py"
    "tests/test_automation_contract.py"
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
  just test tests/test_oracle_projection.py tests/test_homset_projection.py tests/test_provider_role_projection.py tests/test_axiom_projection.py {{args}}

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
test-mutation:
  just test \
    tests/test_manifest.py::test_manifest_semantic_digest_tracks_projection_changes \
    tests/test_manifest.py::test_manifest_semantic_digest_tracks_unsupported_provider_changes \
    tests/test_manifest.py::test_manifest_source_module_digest_tracks_source_hash_changes \
    tests/test_plugin_projection.py::test_plugin_reports_manifest_drift_and_rebuilds_projection \
    tests/test_behavior_matrix.py::test_false_provider_base_reference_is_detected_by_plugin \
    tests/test_behavior_matrix.py::test_false_provider_mro_entry_is_detected_by_plugin \
    -q

[group('test')]
test-performance max_seconds="180":
  #!/usr/bin/env bash
  set -euo pipefail
  started="$(python3 -c 'import time; print(time.monotonic())')"
  just --justfile {{justfile()}} test -q
  finished="$(python3 -c 'import time; print(time.monotonic())')"
  python3 - "$started" "$finished" "{{max_seconds}}" <<'PY'
  import sys

  started = float(sys.argv[1])
  finished = float(sys.argv[2])
  max_seconds = float(sys.argv[3])
  elapsed = finished - started
  print(f"just test -q runtime: {elapsed:.3f}s")
  if elapsed > max_seconds:
      raise SystemExit(
          f"just test -q exceeded {max_seconds:.3f}s performance gate"
      )
  PY

[group('test')]
test-supported-mypy:
  #!/usr/bin/env bash
  set -euo pipefail
  sage -python - <<'PY'
  from __future__ import annotations

  from pathlib import Path
  import tomllib

  from mypy.version import __version__ as mypy_version
  from packaging.requirements import Requirement

  project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
  mypy_requirements = tuple(
      Requirement(dependency)
      for dependency in project["project"]["dependencies"]
      if Requirement(dependency).name == "mypy"
  )
  assert mypy_requirements == (Requirement(f"mypy=={mypy_version}"),), (
      "pyproject must pin exactly the mypy version used by Sage Python: "
      f"{mypy_requirements!r} vs {mypy_version!r}"
  )
  print(f"supported mypy version: {mypy_version}")
  PY

[group('test')]
release-check:
  just test-performance
  just test-supported-mypy
  just test-mutation

[group('build')]
install-sidecar:
  #!/usr/bin/env bash
  set -euo pipefail
  sage -python -m pip install "git+https://github.com/dzackgarza/sage-stubs@c99550bc4056"

[group('build')]
generate-manifest *args:
  #!/usr/bin/env bash
  set -euo pipefail
  export PYTHONPATH="${PWD}${PYTHONPATH:+:${PYTHONPATH}}"
  args=({{args}})
  sage -python -m sage_mypy_category_plugin.resolver "${args[@]}"

[group('build')]
generate-stubs *args:
  #!/usr/bin/env bash
  set -euo pipefail
  export PYTHONPATH="${PWD}${PYTHONPATH:+:${PYTHONPATH}}"
  args=({{args}})
  sage -python -m sage_mypy_category_plugin.stubs "${args[@]}"

[group('validate')]
typecheck *args:
  #!/usr/bin/env bash
  set -euo pipefail
  export PYTHONPATH="${PWD}${PYTHONPATH:+:${PYTHONPATH}}"
  args=({{args}})
  sage -python -m mypy --config-file=/dev/null --ignore-missing-imports --explicit-package-bases sage_mypy_category_plugin tests/test_*.py "${args[@]}"

[group('validate')]
consumer-mypy *args:
  #!/usr/bin/env bash
  set -euo pipefail
  args=({{args}})
  mypy_args=()
  targets=()
  manifest_arg=""
  for arg in "${args[@]}"; do
    if [[ "$arg" == -* ]]; then
      mypy_args+=("$arg")
    elif [[ -f "$arg" && "$arg" == *.json ]]; then
      manifest_arg="$arg"
    else
      targets+=("$arg")
    fi
  done
  if [[ "${#targets[@]}" -eq 0 ]]; then
    targets=(category_specs)
  fi
  mypy_targets=()
  repo_root="${PWD}"
  consumer_root="${SAGE_MYPY_CONSUMER_ROOT:-/home/dzack/research}"
  consumer_package="${consumer_root}/category_specs"
  if [[ ! -d "$consumer_package" ]]; then
    printf 'category_specs consumer tree not found at %s\n' "$consumer_package" >&2
    exit 2
  fi

  config_root="$(mktemp -d)"
  trap 'rm -rf "$config_root"' EXIT
  config_path="${config_root}/mypy.ini"
  cache_dir="${config_root}/sage-category-cache"

  sage -python -m sage_mypy_category_plugin.write_consumer_config "$config_path" "$manifest_arg" "$cache_dir"

  export PYTHONPATH="${repo_root}:${consumer_root}${PYTHONPATH:+:${PYTHONPATH}}"
  cd "$consumer_root"
  for target in "${targets[@]}"; do
    path_target="${target//./\/}"
    if [[ -d "$path_target" ]]; then
      mypy_targets+=("$path_target")
    elif [[ -f "${path_target}.py" ]]; then
      mypy_targets+=("${path_target}.py")
    else
      mypy_targets+=("$target")
    fi
  done
  sage -python -m mypy --config-file "$config_path" "${mypy_targets[@]}" "${mypy_args[@]}"
