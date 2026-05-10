"""Configuration and helpers for the mypy integration test suite."""

import sys
import os

# Ensure that the artificial Sage fixtures are importable as
# ``sage.categories.mypy_test_fixtures.*`` by prepending the fixtures
# directory (which contains the ``sage/`` namespace-package tree) to sys.path.
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
sys.path.insert(0, FIXTURES_DIR)

# Ensure the plugin module itself is importable.
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.abspath(PROJECT_ROOT))
