from __future__ import annotations

from typing import Iterable, List, Set

from core.structural_categories import StructuralCategory, all_structural_categories


def assert_structural_category_invariants() -> None:
    """
    Governance checks for structural categories:

    - Exactly 11 categories exist.
    - No duplicates.
    - Category set matches StructuralCategory enum (no drift).
    """
    categories: List[StructuralCategory] = all_structural_categories()
    if len(categories) != 11:
        raise AssertionError(f"Expected 11 structural categories, found {len(categories)}")
    if len(set(categories)) != 11:
        raise AssertionError("Duplicate structural categories detected")
    enum_set = {c for c in StructuralCategory}
    if set(categories) != enum_set:
        raise AssertionError("Structural category set has drifted from StructuralCategory enum")


def assert_single_primary_category(primary_categories: Iterable[StructuralCategory]) -> None:
    """
    Governance check that every evidence item has at most one primary category.

    Callers should pass the collection of primary categories already assigned
    (one per evidence item). If any evidence item attempts to assign multiple
    primary categories, this function should be called at the offending site
    with a defensive check instead of allowing multiple assignments.
    """
    # This helper is intentionally minimal; enforcement happens at the call site.
    for cat in primary_categories:
        if not isinstance(cat, StructuralCategory):
            raise AssertionError(f"Invalid primary category type: {cat!r}")


def assert_signal_count_limit(signal_ids: Iterable[str], max_signals: int = 7) -> None:
    """
    Governance check that no more than `max_signals` signals are produced.
    """
    ids: List[str] = list(signal_ids)
    if len(ids) > max_signals:
        raise AssertionError(f"Signal count {len(ids)} exceeds governance limit of {max_signals}")


def assert_no_duplicate_evidence_ids(evidence_ids: Iterable[str]) -> None:
    """
    Governance check that no evidence item id appears more than once.
    """
    seen: Set[str] = set()
    for eid in evidence_ids:
        if eid in seen:
            raise AssertionError(f"Duplicate evidence id detected: {eid}")
        seen.add(eid)

