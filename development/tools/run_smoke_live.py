"""
Smoke test: one live run with Search + RSS, structural pipeline enabled, small lookback.
Writes funnel diagnostics and report artifact to development/outputs/.
Run from project root: python -m development.tools.run_smoke_live
"""
from __future__ import annotations

import os
import json
from pathlib import Path
from datetime import datetime

# Force structural pipeline for this run
os.environ["USE_STRUCTURAL_PIPELINE"] = "true"

from core.generator_db import get_specification_detail
from core.generator_execution import execute_generator

BUILDER_EMAIL = "stefan.hermes@htcglobal.asia"
OUTPUTS_DIR = Path("development/outputs")


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    spec_id = os.environ.get("SMOKE_SPEC_ID", "").strip()
    lookback_days_raw = os.environ.get("SMOKE_LOOKBACK_DAYS", "").strip()
    try:
        lookback_days = int(lookback_days_raw) if lookback_days_raw else 7
    except Exception:
        lookback_days = 7
    if lookback_days <= 0:
        lookback_days = 7
    if spec_id:
        spec = get_specification_detail(spec_id)
        if not spec:
            raise SystemExit(f"SMOKE_SPEC_ID {spec_id} not found.")
        workspace_id = spec["workspace_id"]
    else:
        from core.generator_db import get_supabase_client
        supabase = get_supabase_client()
        r = supabase.table("newsletter_specifications").select("id,workspace_id").eq("status", "active").limit(1).execute()
        if not r.data:
            raise SystemExit("No active specification found. Set SMOKE_SPEC_ID or create an active spec.")
        row = r.data[0]
        spec_id = row["id"]
        workspace_id = row["workspace_id"]

    success, err, result_data, artifact_path = execute_generator(
        spec_id=spec_id,
        workspace_id=workspace_id,
        user_email=BUILDER_EMAIL,
        cadence_override=f"{lookback_days}d",
        lookback_override=lookback_days,
    )

    run_id = (result_data or {}).get("run_id") or "unknown"
    diagnostics_path = OUTPUTS_DIR / f"run_{run_id}_diagnostics.json"

    out = {
        "success": success,
        "error": err,
        "run_id": run_id,
        "artifact_path": artifact_path,
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
    }
    if result_data and isinstance(result_data.get("metadata"), dict):
        meta = result_data["metadata"]
        out["evidence_summary"] = meta.get("evidence_summary")
        out["structural_diagnostics"] = meta.get("structural_diagnostics")
        out["funnel"] = (meta.get("evidence_summary") or {}).get("funnel")
        out["drop_buckets"] = (meta.get("evidence_summary") or {}).get("funnel", {}).get("drop_buckets")

    diagnostics_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"Diagnostics written to: {diagnostics_path}")
    if success:
        print("Smoke run succeeded.")
        if out.get("funnel"):
            print("Funnel:", json.dumps(out["funnel"], indent=2))
    else:
        print("Smoke run failed:", err)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
