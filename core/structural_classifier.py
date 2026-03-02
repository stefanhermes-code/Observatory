from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from core.classifier_priority_matrix import classifier_priority_matrix
from core.structural_categories import StructuralCategory
from core.structural_models import ClassificationResult, EvidenceItem


@dataclass(frozen=True)
class ClassificationLog:
    evidence_id: str
    classification_source: str
    primary_category: Optional[StructuralCategory]
    matched_rule_description: Optional[str]


def _combined_text(item: EvidenceItem) -> str:
    """Combine title, snippet and any enrichment text into a single string for rule matching."""
    parts: List[str] = []
    if item.title:
        parts.append(item.title)
    if item.snippet:
        parts.append(item.snippet)
    enrichment = (item.raw_metadata or {}).get("enrichment")
    if isinstance(enrichment, dict):
        txt = enrichment.get("enriched_text")
        if isinstance(txt, str) and txt.strip():
            parts.append(txt)
    return " ".join(p for p in parts if p).strip()


def _llm_classify(_text: str) -> Optional[StructuralCategory]:
    """
    Optional LLM assist hook.

    For now this is a deterministic stub that returns None; wiring to an LLM
    must still obey the governance requirement of choosing strictly from the
    11 structural categories.
    """
    return None


def classify_evidence(
    items: List[EvidenceItem],
) -> Tuple[List[ClassificationResult], List[ClassificationLog], List[str]]:
    """
    Classify evidence into structural categories.

    Returns:
        - list of ClassificationResult (one per classified evidence item)
        - list of ClassificationLog entries (rule/LLM provenance per item)
        - list of evidence_ids that are Lane C and could not be confidently classified
          (UNCLASSIFIED_STRUCTURAL diagnostic bucket).
    """
    rules = classifier_priority_matrix()
    results: List[ClassificationResult] = []
    logs: List[ClassificationLog] = []
    unclassified_lane_c: List[str] = []

    for item in items:
        text = _combined_text(item)
        primary: Optional[StructuralCategory] = None
        matched_desc: Optional[str] = None
        source: str = "rule"

        # 1) Deterministic rule-based matching
        for rule in rules:
            if rule.pattern.search(text):
                primary = rule.category
                matched_desc = rule.description
                break

        # 2) Optional LLM assist if no rule match
        if primary is None:
            source = "llm"
            primary = _llm_classify(text)

        if primary is None:
            # Lane C protection rule: never silently discard
            if item.source_type == "lane_c":
                unclassified_lane_c.append(item.id)
            logs.append(
                ClassificationLog(
                    evidence_id=item.id,
                    classification_source=source,
                    primary_category=None,
                    matched_rule_description=matched_desc,
                )
            )
            continue

        results.append(
            ClassificationResult(
                evidence_id=item.id,
                primary_category=primary,
                secondary_categories=[],
                classification_source=source,
            )
        )
        logs.append(
            ClassificationLog(
                evidence_id=item.id,
                classification_source=source,
                primary_category=primary,
                matched_rule_description=matched_desc,
            )
        )

    return results, logs, unclassified_lane_c

