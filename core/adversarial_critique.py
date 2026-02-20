"""
Phase 6 – Adversarial Critique Layer.
Second-pass quality control after synthesis. Evaluate only; no rewriting.
Returns structured JSON: quality_score (0–10), issues[], requires_revision (bool).
"""

from typing import Dict, List, Any, Optional, Tuple
import json
import re


def run_critique(synthesis_text: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Evaluate Market Intelligence Report draft for analytical rigor and baseline discipline.
    Does not rewrite content. Returns (parsed_result, usage_dict).
    parsed_result: {"quality_score": int 0-10, "issues": ["...", ...], "requires_revision": bool}
    """
    if not (synthesis_text or "").strip():
        return {"quality_score": 0, "issues": ["Empty synthesis."], "requires_revision": True}, None

    from core.openai_assistant import get_openai_client
    client = get_openai_client()
    if not client:
        return None, None

    system = (
        "You are a strict quality reviewer for polyurethane industry market intelligence reports. "
        "You EVALUATE only. You do NOT rewrite, edit, or suggest alternative text. "
        "Do not use external data or assumptions. Do not comment on style or tone preferences. "
        "Focus strictly on: (1) Generic or filler language, (2) Unsupported claims, "
        "(3) Missing quantitative reference when baseline/signal data exists, (4) Weak framing, "
        "(5) Overstatement, (6) Speculative forward risk not grounded in the provided signals. "
        "Output a single JSON object only, no other text. Keys: quality_score (integer 0-10), "
        "issues (array of short diagnostic strings, one line each), requires_revision (boolean). "
        "Set requires_revision true if quality_score < 7 or if any critical issue (unsupported claim, missing baseline reference when data exists, overstatement). "
        "Be strict: prefer requires_revision true when in doubt."
    )
    user = (
        "Evaluate the following Market Intelligence Report draft. "
        "Return only valid JSON: {\"quality_score\": N, \"issues\": [\"...\"], \"requires_revision\": true|false}\n\n"
        "Draft:\n" + (synthesis_text or "")[:8000]
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            max_tokens=800,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        choice = resp.choices[0] if resp.choices else None
        raw = (choice.message.content or "").strip() if choice else ""
        usage = None
        if getattr(resp, "usage", None):
            u = resp.usage
            inp = getattr(u, "input_tokens", None) or getattr(u, "prompt_tokens", 0)
            out = getattr(u, "output_tokens", None) or getattr(u, "completion_tokens", 0)
            tot = getattr(u, "total_tokens", None) or (inp + out)
            usage = {"input_tokens": inp, "output_tokens": out, "total_tokens": tot, "model": resp.model or "gpt-4o-mini"}
        # Parse JSON (allow markdown code block wrapper)
        text = raw
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if m:
            text = m.group(1).strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = {"quality_score": 5, "issues": ["Critique response was not valid JSON."], "requires_revision": True}
        issues = data.get("issues")
        if not isinstance(issues, list):
            data["issues"] = [str(issues)] if issues is not None else []
        data["quality_score"] = max(0, min(10, int(data.get("quality_score", 5))))
        data["requires_revision"] = bool(data.get("requires_revision", True))
        return data, usage
    except Exception:
        return None, None
