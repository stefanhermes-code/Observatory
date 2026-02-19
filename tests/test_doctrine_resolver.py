"""
Phase 4 regression: Doctrine Resolver T1–T6.
Run with: python -m pytest tests/test_doctrine_resolver.py -v
Or: python tests/test_doctrine_resolver.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.doctrine_resolver import resolve


def test_t1_capacity_300k_tpa_structural():
    """T1) Capacity 300,000 TPA -> final_classification structural, override_source doctrine, materiality_flag true."""
    cluster = {"signal_type": "capacity", "aggregated_numeric_value": 300000, "aggregated_numeric_unit": "TPA", "structural_weight": 1}
    out = resolve(cluster, "structural", None)
    assert out["final_classification"] == "structural"
    assert out["override_source"] == "doctrine"
    assert out["materiality_flag"] is True


def test_t2_capacity_neg_30k_tpa_structural():
    """T2) Capacity -30,000 TPA -> final_classification structural, override_source doctrine, materiality_flag true."""
    cluster = {"signal_type": "capacity", "aggregated_numeric_value": -30000, "aggregated_numeric_unit": "TPA", "structural_weight": 1}
    out = resolve(cluster, "tactical", None)
    assert out["final_classification"] == "structural"
    assert out["override_source"] == "doctrine"
    assert out["materiality_flag"] is True


def test_t3_capacity_5k_tpa_follows_llm():
    """T3) Capacity +5,000 TPA -> final_classification follows LLM (no doctrine override)."""
    cluster = {"signal_type": "capacity", "aggregated_numeric_value": 5000, "aggregated_numeric_unit": "TPA", "structural_weight": 1}
    out = resolve(cluster, "tactical", None)
    assert out["final_classification"] == "tactical"
    assert out["override_source"] == "llm"
    assert out["materiality_flag"] is False


def test_t4_demand_8_percent_cyclical():
    """T4) Demand -8% YoY -> final_classification cyclical, override_source doctrine."""
    cluster = {"signal_type": "demand", "aggregated_numeric_value": -8, "aggregated_numeric_unit": "percent", "structural_weight": 0}
    out = resolve(cluster, "structural", None)
    assert out["final_classification"] == "cyclical"
    assert out["override_source"] == "doctrine"


def test_t5_regulation_structural():
    """T5) Regulation -> final_classification structural, override_source doctrine."""
    cluster = {"signal_type": "regulation", "aggregated_numeric_value": None, "aggregated_numeric_unit": None, "structural_weight": 1}
    out = resolve(cluster, "tactical", None)
    assert out["final_classification"] == "structural"
    assert out["override_source"] == "doctrine"
    assert out["materiality_flag"] is True


def test_t6_operational_tactical():
    """T6) Operational (maintenance/outage/logistics/launch) -> final_classification tactical, override_source doctrine."""
    cluster = {"signal_type": "operational", "aggregated_numeric_value": None, "aggregated_numeric_unit": None, "structural_weight": 0}
    out = resolve(cluster, "structural", ["short_term"])
    assert out["final_classification"] == "tactical"
    assert out["override_source"] == "doctrine"
    assert out["materiality_flag"] is False


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
