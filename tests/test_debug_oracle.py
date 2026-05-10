"""Debug oracle tests.

Verifies that the ``debug_projection`` introspection helper correctly
dumps the Sage semantic bases for known real-world categories, and that
the oracle output matches what the plugin would inject.

These tests run inside Sage's Python (imported via ``sage -c``) so they
have access to real Sage categories.
"""

from __future__ import annotations


def _import_debug():
    """Lazy import of the debug oracle function."""
    from sage_mypy_category_plugin.introspection import (
        debug_projection,
        method_container_direct_bases,
    )
    return debug_projection, method_container_direct_bases


# ---------------------------------------------------------------------------
# Debug: Rings
# ---------------------------------------------------------------------------


def test_debug_rings():
    """Rings.ParentMethods → Rngs.ParentMethods (and possibly others)."""
    debug_proj, _ = _import_debug()
    result = debug_proj("sage.categories.rings.Rings.ParentMethods")

    assert "Rngs.ParentMethods" in result, (
        f"Expected Rngs.ParentMethods in debug output, got:\n{result}"
    )
    assert "static bases (from Sage)" in result, (
        f"Expected 'static bases (from Sage)' header, got:\n{result}"
    )


# ---------------------------------------------------------------------------
# Debug: Sets
# ---------------------------------------------------------------------------


def test_debug_sets():
    """Sets.ParentMethods — Sets has no Sage ancestors defining ParentMethods."""
    debug_proj, _ = _import_debug()
    result = debug_proj("sage.categories.sets_cat.Sets.ParentMethods")

    assert "static bases" in result, (
        f"Expected 'static bases' header in output, got:\n{result}"
    )
    # Sets may or may not have bases depending on the Sage version, but the
    # debug oracle should at least print the header and not crash.


# ---------------------------------------------------------------------------
# Debug: Groups
# ---------------------------------------------------------------------------


def test_debug_groups():
    """Groups.ParentMethods → Monoids.ParentMethods."""
    debug_proj, _ = _import_debug()
    result = debug_proj("sage.categories.groups.Groups.ParentMethods")

    assert "Monoids.ParentMethods" in result, (
        f"Expected Monoids.ParentMethods in debug output, got:\n{result}"
    )


# ---------------------------------------------------------------------------
# Oracle matches plugin
# ---------------------------------------------------------------------------


def test_oracle_matches_plugin():
    """The oracle output should show the same bases the plugin would inject."""
    debug_proj, method_container_direct_bases = _import_debug()

    test_cases = [
        "sage.categories.rings.Rings.ParentMethods",
        "sage.categories.fields.Fields.ParentMethods",
    ]

    for fullname in test_cases:
        bases = method_container_direct_bases(fullname)
        oracle = debug_proj(fullname)

        # Every base returned by the function must appear in the oracle output.
        for b in bases:
            assert b in oracle, (
                f"{fullname}: base {b} missing from oracle output:\n{oracle}"
            )


# ---------------------------------------------------------------------------
# Debug: Fields
# ---------------------------------------------------------------------------


def test_debug_fields():
    """Fields.ParentMethods — multi-level inheritance chain."""
    debug_proj, _ = _import_debug()
    result = debug_proj("sage.categories.fields.Fields.ParentMethods")

    # Fields should inherit from at least EuclideanDomains and Rings.
    assert "EuclideanDomains.ParentMethods" in result or "Rings.ParentMethods" in result, (
        f"Expected at least one known ancestor in Fields output, got:\n{result}"
    )
    assert "static bases (from Sage)" in result
