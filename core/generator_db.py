"""
Database operations for Generator app.
Handles newsletter generation, frequency enforcement, and history.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json
from dotenv import load_dotenv

load_dotenv()

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


def get_supabase_client() -> object:
    """Initialize and return Supabase client. Raises exception if not configured."""
    if not SUPABASE_AVAILABLE:
        raise Exception("supabase-py library is not installed. Install with: pip install supabase")
    
    # Streamlit secrets first (Cloud), then env (local .env)
    try:
        import streamlit as st
        supabase_url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
        supabase_key = st.secrets.get("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_ANON_KEY")
    except (AttributeError, FileNotFoundError, RuntimeError):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        raise Exception("Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY in Streamlit Cloud secrets or .env file.")
    
    try:
        client = create_client(supabase_url, supabase_key)
        # Test connection
        client.table("newsletter_specifications").select("id").limit(1).execute()
        return client
    except Exception as e:
        raise Exception(f"Failed to connect to Supabase: {str(e)}. Check your credentials and database connection.")


def get_user_workspaces(user_email: str) -> List[Dict]:
    """Get all workspaces the user belongs to."""
    supabase = get_supabase_client()
    
    # Get user's workspace memberships
    result = supabase.table("workspace_members")\
        .select("workspace_id, workspaces(*)")\
        .eq("user_email", user_email)\
        .execute()
    
    workspaces = []
    if result.data:
        for membership in result.data:
            if membership.get("workspaces"):
                workspaces.append(membership["workspaces"])
    return workspaces


def get_workspace_specifications(workspace_id: str) -> List[Dict]:
    """Get all newsletter specifications for a workspace that are available for generation.
    Includes status 'active' and 'paid_activated' so specs activated in Admin (paid_activated) show in Generator.
    """
    supabase = get_supabase_client()
    result = supabase.table("newsletter_specifications")\
        .select("*")\
        .eq("workspace_id", workspace_id)\
        .in_("status", ["active", "paid_activated"])\
        .execute()
    return result.data if result.data else []


def get_specification_detail(spec_id: str) -> Optional[Dict]:
    """
    Get detailed specification information. Merges DB row with report-option defaults
    from core.report_spec.DEFAULT_REPORT_SPEC (single source of truth per plan §15).
    DB values override; missing report options get defaults.
    """
    from core.report_spec import DEFAULT_REPORT_SPEC

    supabase = get_supabase_client()
    result = supabase.table("newsletter_specifications")\
        .select("*")\
        .eq("id", spec_id)\
        .single()\
        .execute()
    if not result.data:
        return None
    spec = dict(DEFAULT_REPORT_SPEC)
    spec.update(result.data)
    # Flatten report_options JSON into top-level keys so report layer gets full spec
    ro = spec.pop("report_options", None)
    if isinstance(ro, dict):
        spec.update(ro)
    return spec


def check_frequency_enforcement(spec_id: str, frequency: str, user_email: Optional[str] = None) -> tuple[bool, Optional[str], Optional[datetime]]:
    """
    Check if generation is allowed based on frequency limits.
    Returns: (is_allowed, reason_if_blocked, next_eligible_date)
    
    Special backdoor: If user_email is stefan.hermes@htcglobal.asia,
    always allow generation regardless of frequency (for testing and marketing).
    """
    # Backdoor for testing/marketing - always allow for stefan.hermes@htcglobal.asia
    if user_email and user_email.lower() == "stefan.hermes@htcglobal.asia":
        return True, None, None
    
    supabase = get_supabase_client()
    
    # Get successful runs for this specification
    result = supabase.table("newsletter_runs")\
        .select("created_at")\
        .eq("specification_id", spec_id)\
        .eq("status", "success")\
        .order("created_at", desc=True)\
        .limit(1)\
        .execute()
    
    last_success = result.data[0] if result.data else None
    
    now = datetime.utcnow()
    
    if frequency == "daily":
        if last_success:
            last_date = datetime.fromisoformat(last_success["created_at"].replace("Z", "+00:00"))
            if last_date.date() == now.date():
                next_date = now + timedelta(days=1)
                next_date = next_date.replace(hour=0, minute=0, second=0, microsecond=0)
                return False, "Daily limit reached. One newsletter per calendar day.", next_date
        
        return True, None, None
    
    elif frequency == "weekly":
        if last_success:
            last_date = datetime.fromisoformat(last_success["created_at"].replace("Z", "+00:00"))
            # ISO week calculation
            last_week = last_date.isocalendar()[1]
            last_year = last_date.isocalendar()[0]
            current_week = now.isocalendar()[1]
            current_year = now.isocalendar()[0]
            
            if (current_year, current_week) == (last_year, last_week):
                # Calculate next Monday
                days_until_monday = (7 - now.weekday()) % 7
                if days_until_monday == 0:
                    days_until_monday = 7
                next_date = now + timedelta(days=days_until_monday)
                next_date = next_date.replace(hour=0, minute=0, second=0, microsecond=0)
                return False, "Weekly limit reached. One newsletter per ISO week.", next_date
        
        return True, None, None
    
    elif frequency == "monthly":
        if last_success:
            last_date = datetime.fromisoformat(last_success["created_at"].replace("Z", "+00:00"))
            if last_date.year == now.year and last_date.month == now.month:
                # First day of next month
                if now.month == 12:
                    next_date = datetime(now.year + 1, 1, 1)
                else:
                    next_date = datetime(now.year, now.month + 1, 1)
                return False, "Monthly limit reached. One newsletter per calendar month.", next_date
        
        return True, None, None
    
    return True, None, None


def create_newsletter_run(
    spec_id: str,
    workspace_id: str,
    user_email: str,
    status: str = "running",
    frequency: Optional[str] = None,
) -> Dict:
    """Create a new newsletter run record. frequency = cadence used for this run (daily/weekly/monthly)."""
    supabase = get_supabase_client()
    
    run_data = {
        "specification_id": spec_id,
        "workspace_id": workspace_id,
        "user_email": user_email,
        "status": status
    }
    if frequency:
        run_data["frequency"] = frequency.strip().lower()
    
    result = supabase.table("newsletter_runs").insert(run_data).execute()
    return result.data[0] if result.data else run_data


def update_run_status(
    run_id: str,
    status: str,
    artifact_path: Optional[str] = None,
    error_message: Optional[str] = None,
    metadata: Optional[Dict] = None,
    generation_duration_seconds: Optional[float] = None,
    categories_count: Optional[int] = None,
    regions_count: Optional[int] = None,
    links_count: Optional[int] = None,
):
    """Update newsletter run status. Optionally set duration and scope counts (categories, regions, links used in run)."""
    supabase = get_supabase_client()
    update_data = {
        "status": status,
        "completed_at": datetime.utcnow().isoformat() if status in ["success", "failed"] else None
    }
    if artifact_path:
        update_data["artifact_path"] = artifact_path
    if error_message:
        update_data["error_message"] = error_message
    if metadata:
        update_data["metadata"] = metadata
    if generation_duration_seconds is not None:
        update_data["generation_duration_seconds"] = round(generation_duration_seconds, 1)
    if categories_count is not None:
        update_data["categories_count"] = min(32767, max(0, int(categories_count)))
    if regions_count is not None:
        update_data["regions_count"] = min(32767, max(0, int(regions_count)))
    if links_count is not None:
        update_data["links_count"] = min(32767, max(0, int(links_count)))
    supabase.table("newsletter_runs").update(update_data).eq("id", run_id).execute()


def get_specification_history(spec_id: str, limit: int = 50) -> List[Dict]:
    """Get history of runs for a specification."""
    supabase = get_supabase_client()
    try:
        result = supabase.table("newsletter_runs")\
            .select("*")\
            .eq("specification_id", spec_id)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        return result.data if result.data else []
    except Exception as e:
        # Fallback: Try selecting specific columns if * fails
        print(f"Warning: Full select failed for specification history: {e}. Trying fallback.")
        try:
            result = supabase.table("newsletter_runs")\
                .select("id, specification_id, status, created_at, artifact_path, error_message, metadata")\
                .eq("specification_id", spec_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return result.data if result.data else []
        except Exception as e2:
            print(f"Error: Fallback query also failed: {e2}")
            # Return empty list to prevent app crash
            return []


def get_last_successful_run(spec_id: str) -> Optional[Dict]:
    """Get the last successful run for a specification."""
    supabase = get_supabase_client()
    result = supabase.table("newsletter_runs")\
        .select("*")\
        .eq("specification_id", spec_id)\
        .eq("status", "success")\
        .order("created_at", desc=True)\
        .limit(1)\
        .execute()
    return result.data[0] if result.data else None


def get_candidate_articles_for_run(run_id: str) -> List[Dict]:
    """V2: Get all candidate_articles for a run (for extraction and writer)."""
    supabase = get_supabase_client()
    result = supabase.table("candidate_articles")\
        .select("*")\
        .eq("run_id", run_id)\
        .order("published_at", desc=True)\
        .execute()
    return result.data if result.data else []


def get_master_signals_for_run(run_id: str) -> List[Dict[str, Any]]:
    """
    Live master signal view for a run.

    Returns a list of dicts with the canonical fields described in the
    live alignment plan:
      - signal_id, title, url, date, source, query_id
      - category (configurator category from candidate_articles; used to
        map to classifier_category for Phase 5 report sectioning)
      - classifier_category (None; report layer maps from category when needed)
      - tier (reserved; None)

    This is a read-only helper and does not change schema. It provides
    the in-memory master dataset that the customer filter and report
    layer can consume.
    """
    supabase = get_supabase_client()
    result = supabase.table("candidate_articles")\
        .select("id, title, url, published_at, source_name, query_id, category, region, value_chain_link")\
        .eq("run_id", run_id)\
        .order("published_at", desc=True)\
        .execute()
    rows = result.data or []
    signals: List[Dict[str, Any]] = []
    for row in rows:
        signals.append({
            "signal_id": row.get("id"),
            "title": row.get("title"),
            "url": row.get("url"),
            "date": row.get("published_at"),
            "source": row.get("source_name"),
            "query_id": row.get("query_id"),
            "category": row.get("category"),
            "region": row.get("region"),
            "value_chain_link": row.get("value_chain_link"),
            "classifier_category": None,
            "tier": None,
        })
    return signals


def insert_candidate_articles(
    run_id: str,
    workspace_id: str,
    specification_id: str,
    candidates: List[Dict],
) -> int:
    """
    V2: Insert candidate_articles for a run. Deduplicates by (canonical_url, title) within batch
    so one URL (e.g. newsletter page) can have multiple candidates with different titles.
    Each candidate dict: url, canonical_url, title, snippet, published_at, source_id?, source_name,
    query_id?, query_text?, validation_status, http_status.
    Returns count inserted.
    """
    if not candidates:
        return 0
    supabase = get_supabase_client()
    seen: set = set()  # (canonical_url, title_normalized)
    rows = []
    for c in candidates:
        canonical = (c.get("canonical_url") or "").strip()
        title_norm = (c.get("title") or "").strip()
        if not canonical:
            continue
        key = (canonical, title_norm)
        if key in seen:
            continue
        seen.add(key)
        row = {
            "workspace_id": workspace_id,
            "specification_id": specification_id,
            "run_id": run_id,
            "source_id": c.get("source_id"),
            "source_name": c.get("source_name") or "unknown",
            "query_id": c.get("query_id"),
            "query_text": c.get("query_text"),
            "url": (c.get("url") or canonical).strip(),
            "canonical_url": canonical,
            "title": c.get("title"),
            "snippet": c.get("snippet"),
            "published_at": c.get("published_at"),
            "validation_status": c.get("validation_status", "not_checked"),
            "http_status": c.get("http_status"),
            "category": c.get("category"),
            "region": c.get("region"),
            "value_chain_link": c.get("value_chain_link"),
        }
        rows.append(row)
    if not rows:
        return 0
    try:
        supabase.table("candidate_articles").insert(rows).execute()
        return len(rows)
    except Exception:
        return 0


def insert_extracted_signals(run_id: str, signals: List[Dict]) -> int:
    """
    V2 Build Spec Phase 1: insert rows into extracted_signals.
    Each dict: article_id, company_name?, segment, region?, signal_type, numeric_value?, numeric_unit?, currency?,
    time_horizon, confidence_score, raw_json?
    segment/signal_type/time_horizon must be valid enum values (see migration 010).
    Returns count inserted.
    """
    if not signals:
        return 0
    supabase = get_supabase_client()
    rows = []
    for s in signals:
        row = {
            "run_id": run_id,
            "article_id": s.get("article_id"),
            "company_name": s.get("company_name"),
            "segment": s.get("segment", "unknown"),
            "region": s.get("region"),
            "signal_type": s.get("signal_type", "other"),
            "numeric_value": s.get("numeric_value"),
            "numeric_unit": s.get("numeric_unit"),
            "currency": s.get("currency"),
            "time_horizon": s.get("time_horizon", "unknown"),
            "confidence_score": float(s.get("confidence_score", 0)),
            "raw_json": s.get("raw_json"),
        }
        if row["article_id"]:
            rows.append(row)
    if not rows:
        return 0
    try:
        supabase.table("extracted_signals").insert(rows).execute()
        return len(rows)
    except Exception:
        return 0


def get_extracted_signals_for_run(run_id: str) -> List[Dict]:
    """V2 Build Spec: fetch all extracted_signals for a run (for clustering)."""
    supabase = get_supabase_client()
    try:
        result = supabase.table("extracted_signals").select("*").eq("run_id", run_id).execute()
        return result.data if result.data else []
    except Exception:
        return []


def get_article_publish_dates_for_run(run_id: str) -> Dict[str, Any]:
    """
    Phase 5D.1: article_id -> published_at date for candidate_articles of this run.
    Used when building clusters to set cluster_pub_min / cluster_pub_max.
    Returns dict mapping str(article_id) -> date (Python date, or None if published_at missing).
    """
    supabase = get_supabase_client()
    try:
        result = supabase.table("candidate_articles").select("id, published_at").eq("run_id", run_id).execute()
        out = {}
        for row in (result.data or []):
            aid = row.get("id")
            if aid is None:
                continue
            pub = row.get("published_at")
            if pub is None:
                out[str(aid)] = None
                continue
            if isinstance(pub, str) and len(pub) >= 10:
                try:
                    from datetime import date
                    out[str(aid)] = date(int(pub[:4]), int(pub[5:7]), int(pub[8:10]))
                except (ValueError, TypeError):
                    out[str(aid)] = None
            else:
                out[str(aid)] = None
        return out
    except Exception:
        return {}


def insert_signal_clusters(run_id: str, clusters: List[Dict]) -> int:
    """
    V2 Build Spec Phase 2: insert rows into signal_clusters.
    Each dict: cluster_key, signal_type, region?, segment, aggregated_numeric_value?, aggregated_numeric_unit?,
    cluster_size, structural_weight, classification? (optional; Phase 3).
    Phase 5D.1: cluster_pub_min?, cluster_pub_max? (date or None).
    Returns count inserted.
    """
    if not clusters:
        return 0
    supabase = get_supabase_client()
    rows = []
    for c in clusters:
        pub_min = c.get("cluster_pub_min")
        pub_max = c.get("cluster_pub_max")
        row = {
            "run_id": run_id,
            "cluster_key": c.get("cluster_key", ""),
            "signal_type": c.get("signal_type", "other"),
            "region": c.get("region"),
            "segment": c.get("segment", "unknown"),
            "aggregated_numeric_value": c.get("aggregated_numeric_value"),
            "aggregated_numeric_unit": c.get("aggregated_numeric_unit"),
            "cluster_size": int(c.get("cluster_size", 0)),
            "structural_weight": float(c.get("structural_weight", 0)),
            "classification": c.get("classification"),
            "cluster_pub_min": pub_min.isoformat() if hasattr(pub_min, "isoformat") else pub_min,
            "cluster_pub_max": pub_max.isoformat() if hasattr(pub_max, "isoformat") else pub_max,
        }
        if row["cluster_key"]:
            rows.append(row)
    if not rows:
        return 0
    try:
        supabase.table("signal_clusters").insert(rows).execute()
        return len(rows)
    except Exception:
        return 0


def get_signal_clusters_for_run(run_id: str) -> List[Dict]:
    """V2 Build Spec Phase 3: fetch all signal_clusters for a run (for classification)."""
    supabase = get_supabase_client()
    try:
        result = supabase.table("signal_clusters").select("*").eq("run_id", run_id).execute()
        return result.data if result.data else []
    except Exception:
        return []


def update_signal_cluster_classification(cluster_id: str, classification: str) -> bool:
    """V2 Build Spec Phase 3: set classification on one signal_clusters row (llm_classification)."""
    if not cluster_id or not classification:
        return False
    supabase = get_supabase_client()
    try:
        supabase.table("signal_clusters").update({"classification": classification}).eq("id", cluster_id).execute()
        return True
    except Exception:
        return False


def update_signal_cluster_doctrine(
    cluster_id: str,
    final_classification: str,
    override_source: str,
    materiality_flag: bool,
    override_reason: Optional[str] = None,
) -> bool:
    """V2 Build Spec Phase 4: set doctrine resolver output. Does not overwrite classification (llm)."""
    if not cluster_id or not final_classification or override_source not in ("llm", "doctrine"):
        return False
    supabase = get_supabase_client()
    try:
        row = {
            "final_classification": final_classification,
            "override_source": override_source,
            "materiality_flag": materiality_flag,
        }
        if override_reason is not None:
            row["override_reason"] = override_reason
        supabase.table("signal_clusters").update(row).eq("id", cluster_id).execute()
        return True
    except Exception:
        return False

