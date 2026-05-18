set shell := ["bash", "-uc"]

@default:
  just --list

@test *args:
  #!/usr/bin/env bash
  set -euo pipefail
  export PYTHONPATH="${PWD}${PYTHONPATH:+:${PYTHONPATH}}"
  sage -python -m pytest {{args}}
