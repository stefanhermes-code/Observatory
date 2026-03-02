from __future__ import annotations

import json
from pathlib import Path

from core.snapshot_canonicalize import run_snapshot, canonical_json_bytes, sha256_hex, FIXTURE_DIR


def test_pu_observatory_snapshot_regression() -> None:
    """
    Milestone 8 – Deterministic snapshot regression test.

    This test:
    - Loads frozen fixture inputs from development/fixtures/pu_observatory_snapshot/.
    - Replays the structural pipeline offline via snapshot_canonicalize.
    - Builds canonical JSON output and SHA-256 hash.
    - Compares against expected_output.sha256.
    - Fails on any drift.
    """
    base: Path = FIXTURE_DIR
    expected_json_path = base / "expected_output.json"
    expected_hash_path = base / "expected_output.sha256"

    if not expected_json_path.exists() or not expected_hash_path.exists():
        raise AssertionError(
            f"Snapshot baseline files missing in {base}. "
            f"Expected expected_output.json and expected_output.sha256. "
            f"Create them from a real run before running this test."
        )

    # Run snapshot pipeline
    canonical_obj, actual_hash = run_snapshot(base)

    # Load expected baseline
    expected_bytes = expected_json_path.read_bytes()
    expected_obj = json.loads(expected_bytes.decode("utf-8"))
    expected_hash = expected_hash_path.read_text(encoding="utf-8").strip()

    # Re-canonicalize expected to ensure hash consistency
    expected_canonical_bytes = canonical_json_bytes(expected_obj)
    expected_canonical_hash = sha256_hex(expected_canonical_bytes)

    # Hash comparison
    if actual_hash != expected_hash or expected_canonical_hash != expected_hash:
        # Write actual output for inspection
        actual_out_path = base / "actual_output.json"
        actual_out_path.write_bytes(canonical_json_bytes(canonical_obj))

        # Minimal diff summary (counts only to avoid verbose diffs)
        actual_categories = canonical_obj.get("results", {}).get("categories", [])
        expected_categories = expected_obj.get("results", {}).get("categories", [])
        actual_cat_count = len(actual_categories)
        expected_cat_count = len(expected_categories)

        raise AssertionError(
            "PU Observatory snapshot regression failed.\n"
            f"Expected hash: {expected_hash}\n"
            f"Actual hash:   {actual_hash}\n"
            f"Expected canonical hash (from expected_output.json): {expected_canonical_hash}\n"
            f"Category count – expected: {expected_cat_count}, actual: {actual_cat_count}\n"
            f"Full actual canonical output written to: {actual_out_path}"
        )

