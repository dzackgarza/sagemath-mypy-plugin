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
    production_lifecycle
    resolver_cli
    behavior
    automation
  )
  commands=(
    "tests/test_oracle_projection.py tests/test_homset_projection.py tests/test_provider_role_projection.py tests/test_axiom_projection.py"
    "tests/test_manifest.py"
    "tests/test_plugin_projection.py"
    "tests/test_production_lifecycle.py"
    "tests/test_resolver_cli.py"
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
test-production-lifecycle *args:
  just test tests/test_production_lifecycle.py {{args}}

[group('test')]
test-resolver-cli *args:
  just test tests/test_resolver_cli.py {{args}}

[group('test')]
test-behavior *args:
  just test tests/test_behavior_matrix.py tests/test_role_behavior_matrix.py {{args}}

[group('test')]
test-mutation:
  just test \
    tests/test_manifest.py::test_manifest_semantic_digest_tracks_projection_changes \
    tests/test_manifest.py::test_manifest_semantic_digest_tracks_unsupported_provider_changes \
    tests/test_manifest.py::test_manifest_source_module_digest_tracks_source_hash_changes \
    tests/test_plugin_projection.py::test_plugin_recovers_from_corrupt_cache_in_packages_mode \
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
  just test-structural -q
  just test-manifest -q
  just test-production-lifecycle -q
  just test-plugin-projection -q
  just test-behavior -q
  just test tests/test_automation_contract.py -q
  just test-supported-mypy
  just test-mutation

[group('build')]
install-sidecar:
  #!/usr/bin/env bash
  set -euo pipefail
  sage -python -m pip install --force-reinstall "git+https://github.com/dzackgarza/sage-stubs@72b06a042c3b30487b1537bba7461e3bee3b9200"

[group('build')]
generate-manifest *args:
  #!/usr/bin/env bash
  set -euo pipefail
  export PYTHONPATH="${PWD}${PYTHONPATH:+:${PYTHONPATH}}"
  args=({{args}})
  sage -python -m sage_mypy_category_plugin.resolver "${args[@]}"

[group('validate')]
typecheck *args:
  #!/usr/bin/env bash
  set -euo pipefail
  export PYTHONPATH="${PWD}${PYTHONPATH:+:${PYTHONPATH}}"
  args=({{args}})
  sage -python -m mypy --config-file=/dev/null --ignore-missing-imports --explicit-package-bases sage_mypy_category_plugin tests/test_*.py "${args[@]}"

[group('validate')]
consumer-structural *args:
  #!/usr/bin/env bash
  set -euo pipefail
  consumer_root="${SAGE_MYPY_CONSUMER_ROOT:-/home/dzack/research}"
  export PYTHONPATH="${PWD}:${consumer_root}${PYTHONPATH:+:${PYTHONPATH}}"
  args=({{args}})
  sage -python devtools/consumer_structural_canary.py \
    --consumer-root "$consumer_root" \
    --work-dir ".mypy_cache/sage-category-plugin-consumer-canary" \
    "${args[@]}"

[group('validate')]
consumer-structural-fresh *args:
  #!/usr/bin/env bash
  set -euo pipefail
  consumer_root="${SAGE_MYPY_CONSUMER_ROOT:-/home/dzack/research}"
  export PYTHONPATH="${PWD}:${consumer_root}${PYTHONPATH:+:${PYTHONPATH}}"
  args=({{args}})
  work_dir="$(mktemp -d)"
  trap 'rm -rf "${work_dir}"' EXIT
  sage -python devtools/consumer_structural_canary.py \
    --consumer-root "$consumer_root" \
    --work-dir "${work_dir}" \
    "${args[@]}"

[group('validate')]
consumer-structural-all-fresh *args:
  #!/usr/bin/env bash
  set -euo pipefail
  consumer_root="${SAGE_MYPY_CONSUMER_ROOT:-/home/dzack/research}"
  export PYTHONPATH="${PWD}:${consumer_root}${PYTHONPATH:+:${PYTHONPATH}}"
  args=({{args}})
  work_dir="$(mktemp -d)"
  trap 'rm -rf "${work_dir}"' EXIT
  sage -python devtools/consumer_structural_canary.py \
    --consumer-root "$consumer_root" \
    --work-dir "${work_dir}" \
    --all-consumer-modules \
    "${args[@]}"
