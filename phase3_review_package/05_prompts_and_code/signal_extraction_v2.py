"""
V2 Build Spec Phase 1: Structured signal extraction from candidate_articles.
One extraction call per article (gpt-4o-mini); results stored in extracted_signals.
"""

import json
import re
from typing import List, Dict, Any, Optional

# Valid enum values for DB (migration 010)
SEGMENTS = {
    "flexible_foam", "rigid_foam", "tpu", "case", "elastomers",
    "raw_materials", "mixed", "unknown",
}
SIGNAL_TYPES = {
    "capacity", "investment", "mna", "regulation", "feedstock",
    "demand", "sustainability", "price", "operational", "other",
}
TIME_HORIZONS = {"short_term", "cyclical", "structural", "unknown"}


def _coerce_segment(v: Any) -> str:
    if v is None or v == "":
        return "unknown"
    s = str(v).strip().lower().replace("-", "_")
    return s if s in SEGMENTS else "unknown"


def _coerce_signal_type(v: Any) -> str:
    if v is None or v == "":
        return "other"
    s = str(v).strip().lower()
    return s if s in SIGNAL_TYPES else "other"


def _coerce_time_horizon(v: Any) -> str:
    if v is None or v == "":
        return "unknown"
    s = str(v).strip().lower().replace("-", "_")
    return s if s in TIME_HORIZONS else "unknown"


def _extract_json_array(text: str) -> List[Dict]:
    """Parse JSON array from model output; strip markdown code block if present."""
    if not text or not text.strip():
        return []
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("signals", data.get("items", []))
        return []
    except json.JSONDecodeError:
        return []


EXTRACTION_SYSTEM = """You are a polyurethane industry signal extraction engine.
Extract structured market signals only. Do not summarize."""

EXTRACTION_USER_TEMPLATE = """Given the following article:

Title: {title}
Snippet: {snippet}

Extract structured signals in JSON format.

Return JSON array. Each signal must contain:

{{ "company_name": "", "segment": "", "region": "", "signal_type": "", "numeric_value": null, "numeric_unit": "", "currency": "", "time_horizon": "", "confidence_score": 0.0 }}

Rules:
- Extract only explicit information. Do not infer missing numbers.
- If no structural signal, return empty array [].
- Segment must reflect polyurethane context (flexible_foam, rigid_foam, tpu, case, elastomers, raw_materials, mixed, unknown).
- signal_type: one of capacity, investment, mna, regulation, feedstock, demand, sustainability, price, operational, other.
- time_horizon: short_term = operational or tactical; cyclical = demand or price cycle; structural = capacity, regulation, strategic investment; unknown if unclear.
- confidence_score: 0.0 to 1.0.
Return only the JSON array, no other text."""


def _call_extraction(title: str, snippet: str) -> List[Dict]:
    """Single-article extraction call. Returns list of signal dicts (unnormalized)."""
    try:
        import os
        from openai import OpenAI
        try:
            import streamlit as st
            api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        except Exception:
            api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return []
        client = OpenAI(api_key=api_key)
        user_content = EXTRACTION_USER_TEMPLATE.format(
            title=(title or "Untitled")[:500],
            snippet=(snippet or "")[:1500],
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
            max_tokens=1024,
        )
        if not resp.choices or not resp.choices[0].message or not resp.choices[0].message.content:
            return []
        return _extract_json_array(resp.choices[0].message.content)
    except Exception:
        return []


def run_signal_extraction_v2(
    run_id: str,
    candidates: List[Dict],
    batch_size: int = 1,
) -> Dict[str, Any]:
    """
    For each candidate_article, run extraction prompt and store signals in extracted_signals.

    Args:
        run_id: newsletter_runs.id
        candidates: list of candidate_articles rows with id, title, snippet
        batch_size: 1 = one call per article; future: 5–10 for batched calls

    Returns:
        {"extracted_count": N, "signals_inserted": M, "articles_processed": K, "error": optional}
    """
    from core.generator_db import insert_extracted_signals

    if not candidates:
        return {"extracted_count": 0, "signals_inserted": 0, "articles_processed": 0}

    total_inserted = 0
    articles_processed = 0

    for c in candidates:
        article_id = c.get("id")
        if not article_id:
            continue
        title = (c.get("title") or "").strip() or "Untitled"
        snippet = (c.get("snippet") or "").strip()
        raw_signals = _call_extraction(title, snippet)
        articles_processed += 1
        rows = []
        for sig in raw_signals:
            if not isinstance(sig, dict):
                continue
            segment = _coerce_segment(sig.get("segment"))
            signal_type = _coerce_signal_type(sig.get("signal_type"))
            time_horizon = _coerce_time_horizon(sig.get("time_horizon"))
            conf = sig.get("confidence_score")
            if conf is not None:
                try:
                    conf = max(0.0, min(1.0, float(conf)))
                except (TypeError, ValueError):
                    conf = 0.0
            else:
                conf = 0.0
            num_val = sig.get("numeric_value")
            if num_val is not None:
                try:
                    num_val = float(num_val)
                except (TypeError, ValueError):
                    num_val = None
            rows.append({
                "article_id": article_id,
                "company_name": sig.get("company_name") or None,
                "segment": segment,
                "region": (sig.get("region") or "").strip() or None,
                "signal_type": signal_type,
                "numeric_value": num_val,
                "numeric_unit": (sig.get("numeric_unit") or "").strip() or None,
                "currency": (sig.get("currency") or "").strip() or None,
                "time_horizon": time_horizon,
                "confidence_score": conf,
                "raw_json": sig,
            })
        if rows:
            inserted = insert_extracted_signals(run_id, rows)
            total_inserted += inserted

    return {
        "extracted_count": total_inserted,
        "signals_inserted": total_inserted,
        "articles_processed": articles_processed,
    }
