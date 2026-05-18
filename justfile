set shell := ["bash", "-uc"]

@default:
  just --list

@test *args:
  #!/usr/bin/env bash
  set -euo pipefail
  export PYTHONPATH="${PWD}${PYTHONPATH:+:${PYTHONPATH}}"
  sage -python -m pytest {{args}}

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
release-check: test-structural test-manifest test-plugin-projection test-resolver-cli test-stubs test-behavior
