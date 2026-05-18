from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_justfile_exposes_final_state_validation_recipes() -> None:
    result = subprocess.run(
        ("just", "--summary"),
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    recipes = frozenset(result.stdout.split())

    assert {
        "consumer-mypy",
        "generate-manifest",
        "release-check",
        "test",
        "test-behavior",
        "test-manifest",
        "test-mutation",
        "test-performance",
        "test-plugin-projection",
        "test-resolver-cli",
        "test-structural",
        "test-stubs",
        "test-supported-mypy",
        "typecheck",
    } <= recipes


def test_generate_manifest_recipe_forwards_cli_arguments() -> None:
    result = subprocess.run(
        ("just", "--", "generate-manifest", "--help"),
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "category_fullnames" in result.stdout
    assert "--output OUTPUT" in result.stdout
