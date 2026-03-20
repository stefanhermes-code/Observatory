from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


FIXED_REPORT_SECTIONS = [
    "Demand & Market Dynamics",
    "Application & Segment Trends",
    "Capacity & Supply Structure",
    "Corporate & Competitive Moves",
    "Technology & Innovation",
    "Sustainability & Regulation",
]

LEGACY_TO_BLUEPRINT_SECTIONS = {
    "Market Developments": ["Demand & Market Dynamics", "Application & Segment Trends"],
    "Technology and Innovation": ["Technology & Innovation"],
    "Capacity and Investment Activity": ["Capacity & Supply Structure"],
    "Corporate Developments": ["Corporate & Competitive Moves"],
    "Sustainability and Circular Economy": ["Sustainability & Regulation"],
    "Strategic Implications": [],
}

MAX_EXECUTIVE_SUMMARY_ITEMS = 4
MAX_KEY_DEVELOPMENTS = 8
MAX_APPENDIX_REFERENCES = 60

PRODUCT_PATTERNS: List[Tuple[str, Optional[str], List[str]]] = [
    ("adhesives", None, ["adhesive", "adhesives"]),
    ("sealants", None, ["sealant", "sealants"]),
    ("flexible foam", "PU flexible foam", ["pu flex foam", "flex foam", "flexible foam", "slabstock foam", "mattress foam"]),
    ("TPU", "thermoplastic polyurethane", ["thermoplastic polyurethane", "tpu"]),
    ("CASE", None, ["case market", "case markets", "case industry", "case industries", "case and", "coatings adhesives sealants elastomers"]),
    ("rigid foam", None, ["rigid foam", "spray foam", "insulation foam"]),
    ("coatings", None, ["coating", "coatings"]),
    ("elastomers", None, ["elastomer", "elastomers"]),
    ("TDI", "toluene diisocyanate", ["tdi", "toluene diisocyanate"]),
    ("MDI", "methylene diphenyl diisocyanate", ["mdi", "methylene diphenyl diisocyanate"]),
    ("polyols", None, ["polyol", "polyols", "polyether polyol", "polyester polyol"]),
    ("isocyanates", None, ["isocyanate", "isocyanates", "diisocyanate", "diisocyanates"]),
]

SEGMENT_TO_PRODUCT = {
    "flexible_foam": ("flexible foam", ""),
    "rigid_foam": ("rigid foam", ""),
    "tpu": ("TPU", "thermoplastic polyurethane"),
    "case": ("CASE", ""),
    "elastomers": ("elastomers", ""),
    "raw_materials": ("", ""),
    "mixed": ("", ""),
    "unknown": ("", ""),
}

END_USE_PATTERNS: List[Tuple[str, List[str]]] = [
    ("automotive", ["automotive", "vehicle", "vehicles"]),
    ("construction", ["construction", "building", "insulation"]),
    ("footwear", ["footwear", "shoe", "shoes"]),
    ("furniture", ["furniture", "upholstery", "sofa"]),
    ("bedding", ["mattress", "bedding"]),
    ("appliances", ["appliance", "appliances", "refrigerator", "freezer"]),
]

COUNTRY_TO_REGION = {
    "China": "APAC",
    "India": "APAC",
    "Japan": "APAC",
    "South Korea": "APAC",
    "Indonesia": "APAC",
    "Vietnam": "APAC",
    "Thailand": "APAC",
    "Malaysia": "APAC",
    "Singapore": "APAC",
    "Turkey": "EMEA",
    "Germany": "EMEA",
    "France": "EMEA",
    "Italy": "EMEA",
    "Spain": "EMEA",
    "United Kingdom": "EMEA",
    "UK": "EMEA",
    "Netherlands": "EMEA",
    "Belgium": "EMEA",
    "Poland": "EMEA",
    "United States": "North America",
    "USA": "North America",
    "Canada": "North America",
    "Mexico": "Americas",
    "Brazil": "Americas",
}

COUNTRY_PATTERNS: List[Tuple[str, List[str]]] = [
    ("China", [" china ", " chinese "]),
    ("India", [" india ", " indian "]),
    ("Japan", [" japan ", " japanese "]),
    ("South Korea", [" south korea ", " korea "]),
    ("Indonesia", [" indonesia ", " indonesian "]),
    ("Vietnam", [" vietnam ", " vietnamese "]),
    ("Thailand", [" thailand ", " thai "]),
    ("Malaysia", [" malaysia ", " malaysian "]),
    ("Singapore", [" singapore "]),
    ("Turkey", [" turkey ", " turkiye "]),
    ("Germany", [" germany ", " german "]),
    ("France", [" france ", " french "]),
    ("Italy", [" italy ", " italian "]),
    ("Spain", [" spain ", " spanish "]),
    ("United Kingdom", [" united kingdom ", " uk ", " britain ", " british "]),
    ("Netherlands", [" netherlands ", " dutch "]),
    ("Belgium", [" belgium ", " belgian "]),
    ("Poland", [" poland ", " polish "]),
    ("United States", [" united states ", " u.s. ", " usa ", " us "]),
    ("Canada", [" canada ", " canadian "]),
    ("Mexico", [" mexico ", " mexican "]),
    ("Brazil", [" brazil ", " brazilian "]),
]

REGION_PATTERNS: List[Tuple[str, List[str]]] = [
    ("APAC", [" apac ", " asia pacific ", " asia-pacific ", " asia "]),
    ("EMEA", [" emea ", " europe ", " european ", " middle east ", " africa "]),
    ("North America", [" north america ", " united states ", " usa ", " canada "]),
    ("Americas", [" americas ", " latin america ", " south america ", " brazil ", " mexico "]),
    ("Middle East", [" middle east ", " gulf ", " gcc "]),
]

EVENT_PATTERNS: List[Tuple[str, List[str]]] = [
    ("capacity reduction", ["capacity cut", "capacity reduction", "shut down", "closure", "reduce capacity", "halt production"]),
    ("capacity addition", ["capacity expansion", "expand capacity", "new plant", "new facility", "plant expansion", "facility expansion", "increase capacity", "production capacity"]),
    ("market decline", ["decline", "drop", "downturn", "slowdown", "softening", "decrease"]),
    ("market growth", ["growth", "cagr", "market size", "forecast", "outlook", "demand rise", "demand growth", "expansion"]),
    ("regulation / standards", ["regulation", "regulatory", "standards", "standard", "epa", "reach", "compliance", "restriction"]),
    ("partnership / distribution", ["partnership", "partners with", "distribution", "distributor", "collaboration", "alliance", "joint venture", "mou"]),
    ("launch / innovation", ["launch", "innovation", "introduces", "unveils", "technology", "develops", "formulation", "catalyst", "additive"]),
    ("acquisition / corporate move", ["acquisition", "acquires", "acquired", "merger", "divest", "sale", "investment", "restructuring"]),
    ("sustainability / circularity", ["recycling", "circular", "bio-based", "renewable", "decarbonization", "sustainable", "low-carbon"]),
]

UP_PATTERNS = ("growth", "increase", "expansion", "launch", "investment", "rises", "up", "surge")
DOWN_PATTERNS = ("decline", "decrease", "cuts", "closure", "shut", "downturn", "falls", "drop", "softening")
STRUCTURAL_EVENT_TYPES = {
    "regulation / standards",
    "partnership / distribution",
    "launch / innovation",
    "acquisition / corporate move",
    "sustainability / circularity",
}

OFFICIAL_SOURCE_PATTERNS = ("commission", "ministry", "government", "epa", "association", "standard", "agency", "official")
TRUSTED_SOURCE_PATTERNS = ("reuters", "bloomberg", "market", "report", "news", "journal", "industry", "polyurethane", "plastics")

COMPANY_VERBS = (
    "acquires",
    "acquired",
    "expands",
    "launches",
    "partners",
    "invests",
    "opens",
    "announces",
    "builds",
    "develops",
    "unveils",
    "introduces",
    "increases",
    "cuts",
    "signs",
)

COMPANY_STOPWORDS = {
    "apac",
    "emea",
    "europe",
    "asia",
    "india",
    "china",
    "global",
    "polyurethane",
    "market",
    "markets",
    "report",
    "reports",
    "demand",
    "capacity",
}


@dataclass
class NormalizedFact:
    fact_id: str
    source_title: str
    source_name: str
    publication_date: str
    company: str
    region: str
    country: str
    product_family: str
    product_subtype: str
    end_use_segment: str
    event_type: str
    movement_direction: str
    magnitude: str
    unit: str
    time_horizon: str
    theme: str
    confidence: float
    raw_signal_id: str
    cluster_key: str = ""
    cluster_classification: str = ""
    cluster_materiality_flag: bool = False
    cluster_size: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IntelligenceObject:
    object_id: str
    object_type: str
    title: str
    core_theme: str
    related_products: List[str]
    related_regions: List[str]
    related_companies: List[str]
    direction: str
    supporting_fact_ids: List[str]
    evidence_count: int
    contradiction_flag: bool
    confidence_score: float
    strategic_relevance_score: float
    draft_section: str
    draft_implication: str
    evidence_strength: str = "Weak"
    sort_rank: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutiveSummaryItem:
    object_id: str
    title: str
    statement: str
    section: str
    score: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AppendixReference:
    title: str
    source_name: str
    publication_date: str
    sort_date: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data.pop("sort_date", None)
        return data


@dataclass
class ReportBlueprint:
    report_title: str
    reporting_period_label: str
    executive_summary_items: List[ExecutiveSummaryItem]
    key_development_ids: List[str]
    section_allocations: Dict[str, List[str]]
    strategic_implications: List[str]
    appendix_references: List[AppendixReference]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_title": self.report_title,
            "reporting_period_label": self.reporting_period_label,
            "executive_summary_items": [item.to_dict() for item in self.executive_summary_items],
            "key_development_ids": list(self.key_development_ids),
            "section_allocations": {key: list(value) for key, value in self.section_allocations.items()},
            "strategic_implications": list(self.strategic_implications),
            "appendix_references": [item.to_dict() for item in self.appendix_references],
        }


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _normalize_lower(value: str) -> str:
    return f" {_normalize_text(value).lower()} "


def _dedupe_keep_order(values: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values:
        cleaned = _normalize_text(value)
        if not cleaned:
            continue
        if cleaned.lower() in {"unknown", "unspecified", "global/unspecified", "—"}:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out


def _parse_iso_date(value: str) -> Optional[datetime]:
    raw = _normalize_text(value)
    if not raw:
        return None
    for candidate in (raw, raw.replace("Z", "+00:00")):
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            continue
    if len(raw) >= 10:
        try:
            return datetime.strptime(raw[:10], "%Y-%m-%d")
        except ValueError:
            return None
    return None


def _display_date(value: str) -> str:
    parsed = _parse_iso_date(value)
    if parsed is None:
        return _normalize_text(value)
    return parsed.date().isoformat()


def _sort_key_date(value: str) -> str:
    parsed = _parse_iso_date(value)
    if parsed is None:
        return ""
    return parsed.date().isoformat()


def _first_pattern_match(text: str, patterns: Sequence[Tuple[str, Sequence[str]]]) -> str:
    for label, keywords in patterns:
        for keyword in keywords:
            if keyword in text:
                return label
    return ""


def _extract_country(title_text: str) -> str:
    return _first_pattern_match(title_text, COUNTRY_PATTERNS)


def _extract_region(title_text: str, metadata_region: str, country: str) -> str:
    explicit = _normalize_text(metadata_region)
    if explicit:
        return explicit
    pattern_match = _first_pattern_match(title_text, REGION_PATTERNS)
    if pattern_match:
        return pattern_match
    return COUNTRY_TO_REGION.get(country, "")


def _extract_product(title_text: str) -> Tuple[str, str]:
    for family, subtype, keywords in PRODUCT_PATTERNS:
        if any(_keyword_in_text(title_text, keyword) for keyword in keywords):
            return family, subtype or ""
    return "", ""


def _keyword_in_text(title_text: str, keyword: str) -> bool:
    escaped = re.escape(keyword)
    escaped = escaped.replace(r"\ ", r"\s+")
    pattern = rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"
    return bool(re.search(pattern, title_text))


def _segment_product(segment: str) -> Tuple[str, str]:
    return SEGMENT_TO_PRODUCT.get((segment or "unknown").strip().lower(), ("", ""))


def _extract_end_use_segment(title_text: str) -> str:
    return _first_pattern_match(title_text, END_USE_PATTERNS)


def _extract_event_type(title_text: str) -> str:
    return _first_pattern_match(title_text, EVENT_PATTERNS) or "market movement"


def _event_type_from_cluster_signal(cluster_signal_type: str, title_text: str, numeric_value: Optional[float]) -> str:
    title_event = _extract_event_type(title_text)
    if title_event != "market movement":
        return title_event
    signal_type = (cluster_signal_type or "").strip().lower()
    if signal_type == "capacity":
        if numeric_value is not None and float(numeric_value) < 0:
            return "capacity reduction"
        return "capacity addition"
    if signal_type == "demand":
        if numeric_value is not None and float(numeric_value) < 0:
            return "market decline"
        return "market growth"
    if signal_type == "regulation":
        return "regulation / standards"
    if signal_type == "mna":
        return "acquisition / corporate move"
    if signal_type == "sustainability":
        return "sustainability / circularity"
    if signal_type == "investment":
        return "launch / innovation" if "technology" in title_text or "innovation" in title_text else "capacity addition"
    return "market movement"


def _extract_direction(title_text: str, event_type: str) -> str:
    if any(keyword in title_text for keyword in DOWN_PATTERNS):
        return "down"
    if any(keyword in title_text for keyword in UP_PATTERNS):
        return "up"
    if event_type in STRUCTURAL_EVENT_TYPES:
        return "structural"
    if event_type == "capacity addition":
        return "up"
    if event_type == "capacity reduction":
        return "down"
    if event_type == "market growth":
        return "up"
    if event_type == "market decline":
        return "down"
    return "unknown"


def _direction_from_cluster_member(title_text: str, event_type: str, numeric_value: Optional[float]) -> str:
    direction = _extract_direction(title_text, event_type)
    if direction != "unknown":
        return direction
    if numeric_value is not None:
        try:
            if float(numeric_value) > 0:
                return "up"
            if float(numeric_value) < 0:
                return "down"
        except (TypeError, ValueError):
            pass
    return "structural" if event_type in STRUCTURAL_EVENT_TYPES else "unknown"


def _extract_magnitude_and_unit(title: str) -> Tuple[str, str]:
    patterns = [
        re.compile(r"(\d+(?:\.\d+)?)\s?(%)", flags=re.IGNORECASE),
        re.compile(r"([$EURUSD€]?\s?\d+(?:\.\d+)?)\s?(billion|million|bn|mn)", flags=re.IGNORECASE),
        re.compile(r"(\d[\d,\.]*)\s?(ktpa|kta|tons|tonnes|mt|mta|tpa)", flags=re.IGNORECASE),
    ]
    for pattern in patterns:
        match = pattern.search(title or "")
        if match:
            return _normalize_text(match.group(1)), _normalize_text(match.group(2))
    return "", ""


def _extract_time_horizon(title: str) -> str:
    patterns = [
        re.compile(r"\b(20\d{2}\s?-\s?20\d{2})\b"),
        re.compile(r"\b(by|through|to)\s+(20\d{2})\b", flags=re.IGNORECASE),
        re.compile(r"\b(Q[1-4]\s+20\d{2})\b", flags=re.IGNORECASE),
        re.compile(r"\b(H[1-2]\s+20\d{2})\b", flags=re.IGNORECASE),
        re.compile(r"\b(20\d{2})\b"),
    ]
    for pattern in patterns:
        match = pattern.search(title or "")
        if match:
            return _normalize_text(match.group(0))
    return ""


def _time_horizon_from_cluster(title: str, cluster_classification: str, member_time_horizon: str) -> str:
    title_horizon = _extract_time_horizon(title)
    if title_horizon:
        return title_horizon
    member = _normalize_text(member_time_horizon)
    if member and member != "unknown":
        return member
    classification = (cluster_classification or "").strip().lower()
    if classification in {"structural", "transformational", "cyclical", "tactical"}:
        return classification
    return ""


def _extract_company(title: str) -> str:
    cleaned_title = _normalize_text(title)
    if not cleaned_title:
        return ""
    verb_pattern = "|".join(re.escape(verb) for verb in COMPANY_VERBS)
    match = re.search(
        rf"(^|: )([A-Z][A-Za-z0-9&.,'/-]*(?:\s+[A-Z][A-Za-z0-9&.,'/-]*){{0,5}})\s+({verb_pattern})\b",
        cleaned_title,
    )
    if not match:
        return ""
    candidate = match.group(2).strip(" -:,")
    candidate = re.split(r"\s+(?:and|with|&)\s+", candidate, maxsplit=1)[0].strip()
    words = [word for word in re.split(r"\s+", candidate) if word]
    if not words:
        return ""
    if all(word.lower() in COMPANY_STOPWORDS for word in words):
        return ""
    if len(candidate) < 3:
        return ""
    return candidate


def _theme_from_fact(event_type: str, product_family: str, end_use_segment: str) -> str:
    if event_type in {"market growth", "market decline", "market movement"}:
        if end_use_segment:
            return "application demand"
        return "market demand"
    if event_type in {"capacity addition", "capacity reduction"}:
        return "capacity and supply"
    if event_type == "acquisition / corporate move":
        return "competitive positioning"
    if event_type == "partnership / distribution":
        return "route-to-market"
    if event_type == "launch / innovation":
        return "technology and product development"
    if event_type == "regulation / standards":
        return "regulation and standards"
    if event_type == "sustainability / circularity":
        return "sustainability and circularity"
    if product_family:
        return f"{product_family} activity"
    return "polyurethane market activity"


def _fact_confidence(fact: NormalizedFact) -> float:
    extracted_fields = [
        fact.company,
        fact.region,
        fact.country,
        fact.product_family,
        fact.end_use_segment,
        fact.event_type if fact.event_type != "market movement" else "",
        fact.magnitude,
        fact.time_horizon,
    ]
    score = 0.3 + (0.08 * sum(1 for value in extracted_fields if value))
    return round(min(score, 0.95), 2)


def normalize_requested_sections(spec: Optional[Dict[str, Any]]) -> List[str]:
    included = list((spec or {}).get("included_sections") or [])
    if not included:
        return list(FIXED_REPORT_SECTIONS)
    normalized: List[str] = []
    for section in included:
        mapped = LEGACY_TO_BLUEPRINT_SECTIONS.get(section)
        if mapped is None and section in FIXED_REPORT_SECTIONS:
            mapped = [section]
        for item in mapped or []:
            if item not in normalized:
                normalized.append(item)
    return normalized or list(FIXED_REPORT_SECTIONS)


def _strength_from_evidence_count(evidence_count: int) -> str:
    if evidence_count >= 5:
        return "Strong"
    if evidence_count >= 3:
        return "Moderate"
    return "Weak"


def _primary_focus(fact: NormalizedFact) -> str:
    if fact.product_family:
        return fact.product_family
    if fact.end_use_segment:
        return fact.end_use_segment
    if fact.theme == "capacity and supply":
        return "polyurethane capacity"
    if fact.theme == "technology and product development":
        return "polyurethane technology"
    if fact.theme == "sustainability and circularity":
        return "polyurethane sustainability"
    if fact.theme == "regulation and standards":
        return "polyurethane regulation"
    return "polyurethane markets"


def _object_type_for_fact(fact: NormalizedFact) -> str:
    if fact.event_type in {"capacity addition", "capacity reduction"}:
        return "Capacity Move"
    if fact.event_type in {"acquisition / corporate move", "partnership / distribution"}:
        return "Competitive Move"
    if fact.event_type == "launch / innovation":
        return "Technology Move"
    if fact.event_type == "regulation / standards":
        return "Regulatory Shift"
    if fact.event_type == "sustainability / circularity":
        return "Sustainability Shift"
    if fact.event_type in {"market growth", "market decline"}:
        return "Demand Shift"
    return "Demand Shift" if fact.end_use_segment or fact.product_family else "Supply Shift"


def _draft_section_for_object(object_type: str, facts: Sequence[NormalizedFact]) -> str:
    if object_type == "Demand Shift":
        if any(fact.end_use_segment for fact in facts):
            return "Application & Segment Trends"
        return "Demand & Market Dynamics"
    if object_type in {"Supply Shift", "Capacity Move"}:
        return "Capacity & Supply Structure"
    if object_type == "Competitive Move":
        return "Corporate & Competitive Moves"
    if object_type == "Technology Move":
        return "Technology & Innovation"
    if object_type in {"Regulatory Shift", "Sustainability Shift"}:
        return "Sustainability & Regulation"
    if object_type in {"Segment Divergence", "Regional Divergence"}:
        if any(fact.end_use_segment for fact in facts):
            return "Application & Segment Trends"
        return "Demand & Market Dynamics"
    return "Demand & Market Dynamics"


def _object_title(object_type: str, direction: str, facts: Sequence[NormalizedFact]) -> str:
    focus = _primary_focus(facts[0]) if facts else "polyurethane markets"
    regions = _dedupe_keep_order(fact.region or fact.country for fact in facts)
    region_label = ", ".join(regions[:2]) if regions else "key markets"
    if object_type == "Demand Shift":
        if direction == "down":
            return f"{focus} demand softens in {region_label}"
        if direction == "up":
            return f"{focus} demand expands in {region_label}"
        return f"{focus} demand direction remains mixed in {region_label}"
    if object_type == "Supply Shift":
        if direction == "down":
            return f"{focus} supply tightens in {region_label}"
        if direction == "up":
            return f"{focus} supply improves in {region_label}"
        return f"{focus} supply position shifts in {region_label}"
    if object_type == "Capacity Move":
        if direction == "down":
            return f"{focus} contracts in {region_label}" if focus.lower().endswith("capacity") else f"{focus} capacity contracts in {region_label}"
        return f"{focus} expands in {region_label}" if focus.lower().endswith("capacity") else f"{focus} capacity expands in {region_label}"
    if object_type == "Competitive Move":
        return f"Competitive positioning shifts around {focus} in {region_label}"
    if object_type == "Technology Move":
        return f"{focus} innovation activity concentrates in {region_label}"
    if object_type == "Regulatory Shift":
        return f"Standards pressure rises around {focus} in {region_label}"
    if object_type == "Sustainability Shift":
        return f"Sustainability pressure rises around {focus} in {region_label}"
    return f"{focus} intelligence object in {region_label}"


def _object_focus_label(obj: IntelligenceObject) -> str:
    if obj.related_products:
        return ", ".join(obj.related_products[:2])
    if obj.object_type in {"Capacity Move", "Supply Shift"} and obj.core_theme == "capacity and supply":
        return "polyurethane capacity"
    if obj.object_type == "Technology Move" and obj.core_theme == "technology and product development":
        return "polyurethane technology"
    if obj.object_type in {"Regulatory Shift", "Sustainability Shift"} and obj.core_theme in {"sustainability and circularity", "regulation and standards"}:
        return "polyurethane sustainability"
    return obj.core_theme or "polyurethane markets"


def _draft_implication_for_object(object_type: str, direction: str, facts: Sequence[NormalizedFact]) -> str:
    focus = _primary_focus(facts[0]) if facts else "polyurethane markets"
    regions = _dedupe_keep_order(fact.region or fact.country for fact in facts)
    region_label = ", ".join(regions[:2]) if regions else "the referenced markets"
    if object_type == "Demand Shift":
        if direction == "down":
            return f"Commercial planning should separate weakening {focus} demand in {region_label} from stronger lanes elsewhere."
        return f"Commercial coverage and pricing for {focus} should be reweighted toward the markets highlighted in {region_label}."
    if object_type in {"Supply Shift", "Capacity Move"}:
        return f"Supply planning for {focus} should be rechecked against regional availability and asset movement in {region_label}."
    if object_type == "Competitive Move":
        return f"Partnership, acquisition, and channel strategy should be reviewed where competitive activity is clustering in {region_label}."
    if object_type == "Technology Move":
        return f"R&D and commercialization priorities for {focus} should focus on the technology lanes now concentrating in {region_label}."
    if object_type in {"Regulatory Shift", "Sustainability Shift"}:
        return f"Compliance and product-roadmap decisions for {focus} should reflect the policy and transition pressure building in {region_label}."
    return f"Planning assumptions for {focus} should be updated with the latest intelligence from {region_label}."


def _source_quality(source_name: str) -> float:
    name = _normalize_text(source_name).lower()
    if not name:
        return 0.55
    if any(pattern in name for pattern in OFFICIAL_SOURCE_PATTERNS):
        return 1.0
    if any(pattern in name for pattern in TRUSTED_SOURCE_PATTERNS):
        return 0.8
    return 0.65


def _specificity_score(facts: Sequence[NormalizedFact]) -> float:
    checks = [
        any(fact.product_family for fact in facts),
        any(fact.region or fact.country for fact in facts),
        any(fact.company for fact in facts),
        any(fact.end_use_segment for fact in facts),
        any(fact.magnitude for fact in facts),
        any(fact.time_horizon for fact in facts),
    ]
    return sum(1 for item in checks if item) / len(checks)


def _value_chain_relevance(facts: Sequence[NormalizedFact]) -> float:
    if any(fact.product_family or fact.end_use_segment for fact in facts):
        return 1.0
    if any(fact.event_type in {"capacity addition", "capacity reduction", "regulation / standards"} for fact in facts):
        return 0.9
    return 0.7


def _impact_weight(object_type: str) -> float:
    return {
        "Demand Shift": 0.8,
        "Supply Shift": 0.8,
        "Capacity Move": 0.95,
        "Competitive Move": 0.85,
        "Technology Move": 0.75,
        "Regulatory Shift": 0.95,
        "Sustainability Shift": 0.85,
        "Segment Divergence": 1.0,
        "Regional Divergence": 1.0,
    }.get(object_type, 0.7)


def extract_normalized_facts(signals: Sequence[Dict[str, Any]], query_plan_map: Dict[str, Dict[str, str]]) -> List[NormalizedFact]:
    facts: List[NormalizedFact] = []
    for signal in signals:
        title = _normalize_text(signal.get("title") or "")
        if not title:
            continue
        title_text = _normalize_lower(title)
        query_meta = query_plan_map.get(signal.get("query_id") or "") or {}
        country = _extract_country(title_text)
        region = _extract_region(title_text, signal.get("region") or query_meta.get("region") or "", country)
        product_family, product_subtype = _extract_product(title_text)
        end_use_segment = _extract_end_use_segment(title_text)
        event_type = _extract_event_type(title_text)
        direction = _extract_direction(title_text, event_type)
        magnitude, unit = _extract_magnitude_and_unit(title)
        time_horizon = _extract_time_horizon(title)
        fact = NormalizedFact(
            fact_id=str(signal.get("signal_id") or signal.get("id") or f"fact-{len(facts) + 1}"),
            source_title=title,
            source_name=_normalize_text(signal.get("source") or signal.get("source_name") or ""),
            publication_date=_display_date(signal.get("date") or signal.get("published_at") or ""),
            company=_extract_company(title),
            region=region,
            country=country,
            product_family=product_family,
            product_subtype=product_subtype,
            end_use_segment=end_use_segment,
            event_type=event_type,
            movement_direction=direction,
            magnitude=magnitude,
            unit=unit,
            time_horizon=time_horizon,
            theme=_theme_from_fact(event_type, product_family, end_use_segment),
            confidence=0.0,
            raw_signal_id=str(signal.get("signal_id") or signal.get("id") or ""),
        )
        fact.confidence = _fact_confidence(fact)
        facts.append(fact)
    return facts


def extract_normalized_facts_from_clusters(cluster_inputs: Sequence[Dict[str, Any]]) -> List[NormalizedFact]:
    facts: List[NormalizedFact] = []
    seen_fact_ids = set()
    for cluster in cluster_inputs:
        cluster_key = _normalize_text(cluster.get("cluster_key") or "")
        cluster_signal_type = _normalize_text(cluster.get("signal_type") or "")
        cluster_classification = _normalize_text(cluster.get("final_classification") or cluster.get("classification") or "")
        cluster_materiality = bool(cluster.get("materiality_flag"))
        cluster_size = int(cluster.get("cluster_size") or 0)
        cluster_region = _normalize_text(cluster.get("region") or "")
        cluster_numeric_value = cluster.get("aggregated_numeric_value")
        cluster_numeric_unit = _normalize_text(cluster.get("aggregated_numeric_unit") or "")
        segment_family, segment_subtype = _segment_product(cluster.get("segment") or "")

        for member in cluster.get("supporting_signals") or []:
            title = _normalize_text(member.get("source_title") or "")
            if not title:
                continue
            title_text = _normalize_lower(title)
            raw_signal_id = str(member.get("signal_id") or member.get("article_id") or "")
            fact_id = raw_signal_id or f"{cluster_key}:{len(facts) + 1}"
            if fact_id in seen_fact_ids:
                continue
            seen_fact_ids.add(fact_id)
            country = _extract_country(title_text)
            region = _extract_region(title_text, member.get("region") or member.get("article_region") or cluster_region, country)
            product_family, product_subtype = _extract_product(title_text)
            if not product_family:
                product_family, product_subtype = segment_family, segment_subtype
            end_use_segment = _extract_end_use_segment(title_text)
            event_type = _event_type_from_cluster_signal(cluster_signal_type, title_text, cluster_numeric_value)
            direction = _direction_from_cluster_member(title_text, event_type, cluster_numeric_value)
            magnitude, unit = _extract_magnitude_and_unit(title)
            if not magnitude and cluster_numeric_value is not None:
                magnitude = _normalize_text(str(cluster_numeric_value))
                unit = cluster_numeric_unit or unit
            fact = NormalizedFact(
                fact_id=fact_id,
                source_title=title,
                source_name=_normalize_text(member.get("source_name") or ""),
                publication_date=_display_date(member.get("publication_date") or cluster.get("cluster_pub_max") or ""),
                company=_normalize_text(member.get("company_name") or _extract_company(title)),
                region=region,
                country=country,
                product_family=product_family,
                product_subtype=product_subtype,
                end_use_segment=end_use_segment,
                event_type=event_type,
                movement_direction=direction,
                magnitude=magnitude,
                unit=unit,
                time_horizon=_time_horizon_from_cluster(title, cluster_classification, member.get("time_horizon") or ""),
                theme=_theme_from_fact(event_type, product_family, end_use_segment),
                confidence=0.0,
                raw_signal_id=raw_signal_id,
                cluster_key=cluster_key,
                cluster_classification=cluster_classification,
                cluster_materiality_flag=cluster_materiality,
                cluster_size=cluster_size,
            )
            fact.confidence = min(0.99, _fact_confidence(fact) + (0.08 if cluster_materiality else 0.0) + (0.04 if cluster_classification in {"structural", "transformational"} else 0.0))
            facts.append(fact)
    return facts


def build_intelligence_objects(facts: Sequence[NormalizedFact]) -> List[IntelligenceObject]:
    grouped: Dict[Tuple[str, str, str, str, str], List[NormalizedFact]] = defaultdict(list)
    for fact in facts:
        object_type = _object_type_for_fact(fact)
        focus = (_primary_focus(fact) or "polyurethane markets").lower()
        region = (fact.region or fact.country or "key markets").lower()
        company = fact.company.lower() if object_type == "Competitive Move" else ""
        direction = fact.movement_direction if fact.movement_direction in {"up", "down"} else "structural"
        grouped[(object_type, focus, region, company, direction)].append(fact)

    objects: List[IntelligenceObject] = []
    for index, ((object_type, _focus, _region, _company, direction), grouped_facts) in enumerate(grouped.items(), start=1):
        related_products = _dedupe_keep_order(
            [fact.product_family for fact in grouped_facts]
            + [fact.product_subtype for fact in grouped_facts]
            + [fact.end_use_segment for fact in grouped_facts]
        )
        related_regions = _dedupe_keep_order([fact.region for fact in grouped_facts] + [fact.country for fact in grouped_facts])
        related_companies = _dedupe_keep_order(fact.company for fact in grouped_facts)
        confidence_score = round(mean(fact.confidence for fact in grouped_facts), 2)
        draft_section = _draft_section_for_object(object_type, grouped_facts)
        object_id = f"io-{index:03d}"
        obj = IntelligenceObject(
            object_id=object_id,
            object_type=object_type,
            title=_object_title(object_type, direction, grouped_facts),
            core_theme=grouped_facts[0].theme,
            related_products=related_products,
            related_regions=related_regions,
            related_companies=related_companies,
            direction=direction,
            supporting_fact_ids=[fact.fact_id for fact in grouped_facts],
            evidence_count=len(grouped_facts),
            contradiction_flag=False,
            confidence_score=confidence_score,
            strategic_relevance_score=0.0,
            draft_section=draft_section,
            draft_implication=_draft_implication_for_object(object_type, direction, grouped_facts),
            evidence_strength=_strength_from_evidence_count(len(grouped_facts)),
        )
        objects.append(obj)
    return objects


def resolve_contradictions(objects: Sequence[IntelligenceObject], facts_by_id: Dict[str, NormalizedFact]) -> List[IntelligenceObject]:
    resolved: List[IntelligenceObject] = list(objects)
    existing_titles = {obj.title.lower() for obj in resolved}
    next_id = len(resolved) + 1

    def add_object(title: str, object_type: str, base_objects: Sequence[IntelligenceObject], section: str, implication: str) -> None:
        nonlocal next_id
        if title.lower() in existing_titles:
            return
        supporting_fact_ids = _dedupe_keep_order(
            fact_id for obj in base_objects for fact_id in obj.supporting_fact_ids
        )
        base_facts = [facts_by_id[fact_id] for fact_id in supporting_fact_ids if fact_id in facts_by_id]
        related_products = _dedupe_keep_order(product for obj in base_objects for product in obj.related_products)
        related_regions = _dedupe_keep_order(region for obj in base_objects for region in obj.related_regions)
        related_companies = _dedupe_keep_order(company for obj in base_objects for company in obj.related_companies)
        confidence_score = round(mean([obj.confidence_score for obj in base_objects]) if base_objects else 0.5, 2)
        evidence_count = len(supporting_fact_ids)
        resolved.append(
            IntelligenceObject(
                object_id=f"io-{next_id:03d}",
                object_type=object_type,
                title=title,
                core_theme=base_objects[0].core_theme if base_objects else "market divergence",
                related_products=related_products,
                related_regions=related_regions,
                related_companies=related_companies,
                direction="mixed",
                supporting_fact_ids=supporting_fact_ids,
                evidence_count=evidence_count,
                contradiction_flag=True,
                confidence_score=confidence_score,
                strategic_relevance_score=0.0,
                draft_section=section,
                draft_implication=implication,
                evidence_strength=_strength_from_evidence_count(evidence_count),
            )
        )
        existing_titles.add(title.lower())
        next_id += 1

    by_object_focus: Dict[Tuple[str, str], List[IntelligenceObject]] = defaultdict(list)
    for obj in objects:
        primary_product = obj.related_products[0] if obj.related_products else obj.core_theme
        by_object_focus[(obj.object_type, primary_product.lower())].append(obj)

    for (object_type, focus), bucket in by_object_focus.items():
        ups = [obj for obj in bucket if obj.direction == "up"]
        downs = [obj for obj in bucket if obj.direction == "down"]
        if ups and downs:
            display_focus = (
                (ups[0].related_products[0] if ups[0].related_products else "")
                or (downs[0].related_products[0] if downs[0].related_products else "")
                or focus
            )
            up_regions = _dedupe_keep_order(region for obj in ups for region in obj.related_regions)
            down_regions = _dedupe_keep_order(region for obj in downs for region in obj.related_regions)
            title = f"{display_focus} diverges between {'/'.join(up_regions[:2])} and {'/'.join(down_regions[:2])}"
            implication = f"Planning should not treat {display_focus} as one uniform market because the evidence splits between stronger and weaker regional lanes."
            add_object(title, "Regional Divergence", ups[:1] + downs[:1], "Demand & Market Dynamics", implication)

    region_direction_groups: Dict[str, Dict[str, List[IntelligenceObject]]] = defaultdict(lambda: defaultdict(list))
    for obj in objects:
        if obj.object_type != "Demand Shift":
            continue
        for region in obj.related_regions or ["key markets"]:
            region_direction_groups[region][obj.direction].append(obj)

    for region, direction_map in region_direction_groups.items():
        ups = direction_map.get("up") or []
        downs = direction_map.get("down") or []
        if ups and downs:
            up_focus = ups[0].related_products[0] if ups[0].related_products else ups[0].core_theme
            down_focus = downs[0].related_products[0] if downs[0].related_products else downs[0].core_theme
            if up_focus.lower() == down_focus.lower():
                continue
            title = f"Segment demand diverges in {region}: {up_focus} strengthens while {down_focus} softens"
            implication = f"Segment planning in {region} should separate the expanding and contracting lanes instead of using one aggregate demand assumption."
            add_object(title, "Segment Divergence", [ups[0], downs[0]], "Application & Segment Trends", implication)

    for demand_obj in [obj for obj in objects if obj.object_type == "Demand Shift" and obj.direction == "up"]:
        same_region_capacity = [
            obj for obj in objects
            if obj.object_type == "Capacity Move"
            and set(obj.related_regions).intersection(set(demand_obj.related_regions))
            and (
                not demand_obj.related_products
                or not obj.related_products
                or set(obj.related_products).intersection(set(demand_obj.related_products))
            )
        ]
        if same_region_capacity and all(obj.direction != "up" for obj in same_region_capacity):
            focus = demand_obj.related_products[0] if demand_obj.related_products else demand_obj.core_theme
            region = demand_obj.related_regions[0] if demand_obj.related_regions else "key markets"
            title = f"Demand strengthens faster than supply signals for {focus} in {region}"
            implication = f"Demand planning for {focus} in {region} should be paired with tighter supply monitoring because capacity evidence is not keeping pace."
            add_object(title, "Supply Shift", [demand_obj] + same_region_capacity[:1], "Capacity & Supply Structure", implication)

    for sustain_obj in [obj for obj in objects if obj.object_type in {"Regulatory Shift", "Sustainability Shift"}]:
        same_region_capacity = [
            obj for obj in objects
            if obj.object_type == "Capacity Move"
            and set(obj.related_regions).intersection(set(sustain_obj.related_regions))
        ]
        if same_region_capacity and all(obj.direction != "up" for obj in same_region_capacity):
            focus = sustain_obj.related_products[0] if sustain_obj.related_products else "polyurethane markets"
            region = sustain_obj.related_regions[0] if sustain_obj.related_regions else "key markets"
            title = f"Sustainability pressure rises around {focus} while capacity moves remain limited in {region}"
            implication = f"Transition planning in {region} should not rely on large-scale asset movement when sustainability pressure is rising faster than capacity change."
            add_object(title, "Sustainability Shift", [sustain_obj], "Sustainability & Regulation", implication)

    for tech_obj in [obj for obj in objects if obj.object_type == "Technology Move"]:
        same_scope_scaling = [
            obj for obj in objects
            if obj.object_type in {"Capacity Move", "Competitive Move"}
            and set(obj.related_regions).intersection(set(tech_obj.related_regions))
            and (
                not tech_obj.related_products
                or not obj.related_products
                or set(obj.related_products).intersection(set(tech_obj.related_products))
            )
        ]
        if not same_scope_scaling:
            focus = tech_obj.related_products[0] if tech_obj.related_products else tech_obj.core_theme
            region = tech_obj.related_regions[0] if tech_obj.related_regions else "key markets"
            title = f"Innovation activity is rising in {focus} across {region}, but commercial scaling remains unclear"
            implication = f"Technology progress in {focus} should be tracked separately from commercialization because scaling evidence is still limited in {region}."
            add_object(title, "Technology Move", [tech_obj], "Technology & Innovation", implication)

    return resolved


def rank_intelligence_objects(objects: Sequence[IntelligenceObject], facts_by_id: Dict[str, NormalizedFact]) -> List[IntelligenceObject]:
    ranked: List[IntelligenceObject] = []
    for obj in objects:
        facts = [facts_by_id[fact_id] for fact_id in obj.supporting_fact_ids if fact_id in facts_by_id]
        if not facts:
            continue
        evidence_density = min(obj.evidence_count / 6.0, 1.0)
        source_quality = mean(_source_quality(fact.source_name) for fact in facts)
        specificity = _specificity_score(facts)
        quantitative = 1.0 if any(fact.magnitude for fact in facts) else 0.0
        cross_region = 1.0 if len(obj.related_regions) > 1 else 0.0
        value_chain = _value_chain_relevance(facts)
        impact = _impact_weight(obj.object_type)
        contradiction = 1.0 if obj.contradiction_flag else 0.0
        materiality = 1.0 if any(fact.cluster_materiality_flag for fact in facts) else 0.0
        cluster_classification = 1.0 if any(fact.cluster_classification in {"structural", "transformational"} for fact in facts) else 0.5 if any(fact.cluster_classification == "cyclical" for fact in facts) else 0.0
        anchor_penalty = 0.0
        if not obj.related_products:
            anchor_penalty += 8.0
        if not obj.related_regions:
            anchor_penalty += 5.0
        total = (
            25 * evidence_density
            + 15 * source_quality
            + 15 * specificity
            + 10 * quantitative
            + 10 * cross_region
            + 10 * value_chain
            + 5 * impact
            + 5 * contradiction
            + 3 * materiality
            + 2 * cluster_classification
        )
        obj.strategic_relevance_score = round(max(total - anchor_penalty, 0), 2)
        obj.confidence_score = round(mean(fact.confidence for fact in facts), 2)
        ranked.append(obj)
    ranked.sort(
        key=lambda obj: (
            -obj.strategic_relevance_score,
            -obj.evidence_count,
            -obj.confidence_score,
            obj.title.lower(),
        )
    )
    for index, obj in enumerate(ranked, start=1):
        obj.sort_rank = index
    return ranked


def _object_market_statement(obj: IntelligenceObject) -> str:
    focus = _object_focus_label(obj)
    region = ", ".join(obj.related_regions[:2]) if obj.related_regions else "the referenced markets"
    if obj.object_type == "Demand Shift":
        if obj.direction == "down":
            return f"Demand for {focus} is softening in {region}, and the supporting evidence points to weaker market momentum rather than a broad-based expansion."
        if obj.direction == "up":
            return f"Demand for {focus} is expanding in {region}, with repeated market evidence pointing to stronger buyer activity and clearer growth lanes."
        return f"Demand conditions for {focus} remain mixed in {region}, so the market cannot be described as moving in one uniform direction."
    if obj.object_type in {"Supply Shift", "Capacity Move"}:
        if obj.direction == "down":
            return f"Supply conditions for {focus} are tightening in {region}, which increases the importance of regional continuity and allocation decisions."
        if obj.direction == "up":
            return f"Supply structure for {focus} is expanding in {region}, shifting expectations for future availability and competitive positioning."
        return f"Supply structure for {focus} is changing in {region}, and the direction of that shift matters for near-term planning."
    if obj.object_type == "Competitive Move":
        return f"Competitive positioning around {focus} is shifting in {region}, with corporate activity affecting channel access, reach, and value-chain presence."
    if obj.object_type == "Technology Move":
        if obj.contradiction_flag:
            return f"Technology activity around {focus} is active in {region}, but the evidence still separates innovation signals from confirmed commercial scaling."
        return f"Technology activity around {focus} is concentrating in {region}, pointing to nearer-term movement in formulation, process, or application capability."
    if obj.object_type == "Regulatory Shift":
        return f"Regulatory pressure affecting {focus} is increasing in {region}, pushing compliance and product decisions onto a tighter timetable."
    if obj.object_type == "Sustainability Shift":
        if obj.contradiction_flag:
            return f"Sustainability pressure is rising around {focus} in {region}, while asset and supply-side movement remain more limited than the transition rhetoric."
        return f"Sustainability and circularity activity around {focus} is building in {region}, shifting sourcing and product-roadmap priorities."
    if obj.object_type == "Segment Divergence":
        return f"Segment conditions are diverging in {region}, and the supporting evidence points to winners and laggards rather than one shared trajectory."
    if obj.object_type == "Regional Divergence":
        return f"Regional conditions for {focus} are diverging, so the same reporting window supports different conclusions across geographies."
    return f"Market conditions for {focus} are moving in {region}, and the development is material enough to change planning priorities."


def _executive_statement(obj: IntelligenceObject) -> str:
    return f"{obj.title}. {_object_market_statement(obj)}"


def _strategic_implication_line(obj: IntelligenceObject) -> str:
    return f"{obj.title}: {obj.draft_implication}"


def _has_specific_anchor(obj: IntelligenceObject) -> bool:
    return bool(obj.related_products or obj.related_companies or obj.contradiction_flag)


def _object_signature(obj: IntelligenceObject) -> Tuple[str, str, str]:
    focus = (obj.related_products[0] if obj.related_products else obj.core_theme or obj.title).lower()
    region = (obj.related_regions[0] if obj.related_regions else "").lower()
    return (obj.draft_section.lower(), focus, region)


def _limit_section_objects(objects: Sequence[IntelligenceObject], max_items: int = 4) -> List[IntelligenceObject]:
    limited: List[IntelligenceObject] = []
    seen = set()
    for obj in objects:
        signature = _object_signature(obj)
        if signature in seen:
            continue
        seen.add(signature)
        limited.append(obj)
        if len(limited) >= max_items:
            break
    return limited


def build_report_blueprint(
    ranked_objects: Sequence[IntelligenceObject],
    facts_by_id: Dict[str, NormalizedFact],
    spec: Optional[Dict[str, Any]],
    report_period_days: Optional[int],
) -> ReportBlueprint:
    requested_sections = set(normalize_requested_sections(spec))
    min_strength = (spec or {}).get("minimum_signal_strength_in_report")
    strength_order = {"Weak": 1, "Moderate": 2, "Strong": 3}
    threshold = strength_order.get(min_strength, 1) if min_strength else 1
    eligible_objects = [
        obj for obj in ranked_objects
        if obj.draft_section in requested_sections and strength_order.get(obj.evidence_strength, 1) >= threshold
    ]

    blueprint_candidates = [obj for obj in eligible_objects if _has_specific_anchor(obj)]
    if not blueprint_candidates:
        blueprint_candidates = list(eligible_objects)

    reportable_candidates = [
        obj for obj in blueprint_candidates
        if obj.contradiction_flag or obj.evidence_count >= 2 or obj.strategic_relevance_score >= 55
    ]
    if not reportable_candidates:
        reportable_candidates = list(blueprint_candidates)

    exec_items: List[ExecutiveSummaryItem] = []
    used_sections = set()
    for obj in reportable_candidates:
        if obj.draft_section in used_sections:
            continue
        exec_items.append(
            ExecutiveSummaryItem(
                object_id=obj.object_id,
                title=obj.title,
                statement=_executive_statement(obj),
                section=obj.draft_section,
                score=obj.strategic_relevance_score,
            )
        )
        used_sections.add(obj.draft_section)
        if len(exec_items) >= MAX_EXECUTIVE_SUMMARY_ITEMS:
            break
    if len(exec_items) < MAX_EXECUTIVE_SUMMARY_ITEMS:
        used_ids = {item.object_id for item in exec_items}
        for obj in reportable_candidates:
            if obj.object_id in used_ids:
                continue
            exec_items.append(
                ExecutiveSummaryItem(
                    object_id=obj.object_id,
                    title=obj.title,
                    statement=_executive_statement(obj),
                    section=obj.draft_section,
                    score=obj.strategic_relevance_score,
                )
            )
            if len(exec_items) >= MAX_EXECUTIVE_SUMMARY_ITEMS:
                break

    key_candidates = [
        obj for obj in reportable_candidates
        if obj.contradiction_flag or obj.evidence_count >= 2 or obj.strategic_relevance_score >= 60
    ]
    key_developments = [obj.object_id for obj in _limit_section_objects(key_candidates, max_items=MAX_KEY_DEVELOPMENTS)]
    section_allocations = {}
    for section in FIXED_REPORT_SECTIONS:
        section_objects = [obj for obj in reportable_candidates if obj.draft_section == section]
        section_allocations[section] = [obj.object_id for obj in _limit_section_objects(section_objects, max_items=3)]

    strategic_implications = [
        _strategic_implication_line(obj)
        for obj in _limit_section_objects(reportable_candidates, max_items=MAX_EXECUTIVE_SUMMARY_ITEMS)
    ]

    appendix_refs: List[AppendixReference] = []
    seen_refs = set()
    for obj in eligible_objects:
        for fact_id in obj.supporting_fact_ids:
            fact = facts_by_id.get(fact_id)
            if not fact:
                continue
            key = (fact.source_title.lower(), fact.source_name.lower())
            if key in seen_refs:
                continue
            seen_refs.add(key)
            appendix_refs.append(
                AppendixReference(
                    title=fact.source_title,
                    source_name=fact.source_name or "Unknown source",
                    publication_date=fact.publication_date or "Unknown date",
                    sort_date=_sort_key_date(fact.publication_date),
                )
            )
    appendix_refs.sort(key=lambda item: item.sort_date, reverse=True)
    appendix_refs = appendix_refs[:MAX_APPENDIX_REFERENCES]

    if isinstance(report_period_days, int) and report_period_days > 0:
        period_label = f"{report_period_days}-day window"
    else:
        period_label = "30-day window"

    return ReportBlueprint(
        report_title=(spec or {}).get("report_title") or "Polyurethane Industry Intelligence Briefing",
        reporting_period_label=period_label,
        executive_summary_items=exec_items,
        key_development_ids=key_developments,
        section_allocations=section_allocations,
        strategic_implications=strategic_implications,
        appendix_references=appendix_refs,
    )


def render_report_blueprint(blueprint: ReportBlueprint, ranked_objects: Sequence[IntelligenceObject]) -> str:
    object_map = {obj.object_id: obj for obj in ranked_objects}
    lines: List[str] = [
        f"# {blueprint.report_title}",
        "",
        f"*Reporting period: {blueprint.reporting_period_label}*",
        "",
        "## Executive Summary",
        "",
    ]

    if blueprint.executive_summary_items:
        for item in blueprint.executive_summary_items:
            lines.append(f"- {item.statement}")
    else:
        lines.append("- No intelligence objects cleared the current report thresholds.")
    lines.extend(["", "## Key Developments", ""])

    if blueprint.key_development_ids:
        for object_id in blueprint.key_development_ids:
            obj = object_map.get(object_id)
            if not obj:
                continue
            lines.extend(
                [
                    f"### {obj.title}",
                    "",
                    _object_market_statement(obj),
                    "",
                    f"Implication: {obj.draft_implication}",
                    "",
                    f"Evidence base: {obj.evidence_count} referenced items; relevance score {obj.strategic_relevance_score}.",
                    "",
                ]
            )
    else:
        lines.extend(["No developments were available after ranking and thresholding.", ""])

    for section in FIXED_REPORT_SECTIONS:
        lines.extend([f"## {section}", ""])
        section_ids = blueprint.section_allocations.get(section) or []
        if not section_ids:
            lines.extend(["No ranked intelligence objects were allocated to this section for the current run.", ""])
            continue
        for object_id in section_ids:
            obj = object_map.get(object_id)
            if not obj:
                continue
            lines.extend(
                [
                    f"### {obj.title}",
                    "",
                    _object_market_statement(obj),
                    "",
                    f"Implication: {obj.draft_implication}",
                    "",
                    f"Evidence base: {obj.evidence_count} referenced items; confidence {obj.confidence_score}.",
                    "",
                ]
            )

    lines.extend(["## Strategic Implications", ""])
    if blueprint.strategic_implications:
        for item in blueprint.strategic_implications:
            lines.append(f"- {item}")
    else:
        lines.append("- Strategic implications are unavailable because no ranked intelligence objects were produced.")

    lines.extend(["", "## Appendix A - Sources", ""])
    if blueprint.appendix_references:
        for item in blueprint.appendix_references:
            lines.extend(
                [
                    item.title,
                    f"Source: {item.source_name}",
                    f"Publication date: {item.publication_date}",
                    "",
                ]
            )
    else:
        lines.append("No appendix references were available.")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_intelligence_report(
    filtered_signals: Sequence[Dict[str, Any]],
    query_plan_map: Dict[str, Dict[str, str]],
    spec: Optional[Dict[str, Any]],
    report_period_days: Optional[int],
) -> Dict[str, Any]:
    facts = extract_normalized_facts(filtered_signals, query_plan_map)
    facts_by_id = {fact.fact_id: fact for fact in facts}
    base_objects = build_intelligence_objects(facts)
    resolved_objects = resolve_contradictions(base_objects, facts_by_id)
    ranked_objects = rank_intelligence_objects(resolved_objects, facts_by_id)
    blueprint = build_report_blueprint(ranked_objects, facts_by_id, spec, report_period_days)
    report_text = render_report_blueprint(blueprint, ranked_objects)

    return {
        "report_text": report_text,
        "facts": [fact.to_dict() for fact in facts],
        "intelligence_objects": [obj.to_dict() for obj in ranked_objects],
        "blueprint": blueprint.to_dict(),
        "metrics": build_report_metrics(
            filtered_signals_count=len(filtered_signals),
            facts=facts,
            base_object_count=len(base_objects),
            ranked_objects=ranked_objects,
            blueprint=blueprint,
        ),
    }


def build_intelligence_report_from_cluster_inputs(
    cluster_inputs: Sequence[Dict[str, Any]],
    fallback_signals: Sequence[Dict[str, Any]],
    query_plan_map: Dict[str, Dict[str, str]],
    spec: Optional[Dict[str, Any]],
    report_period_days: Optional[int],
) -> Dict[str, Any]:
    cluster_facts = extract_normalized_facts_from_clusters(cluster_inputs)
    covered_signal_ids = {fact.raw_signal_id for fact in cluster_facts if fact.raw_signal_id}
    fallback_candidates = [
        signal for signal in fallback_signals
        if str(signal.get("signal_id") or signal.get("id") or "") not in covered_signal_ids
    ]
    fallback_facts = extract_normalized_facts(fallback_candidates, query_plan_map)
    facts = cluster_facts + fallback_facts
    facts_by_id = {fact.fact_id: fact for fact in facts}
    base_objects = build_intelligence_objects(facts)
    resolved_objects = resolve_contradictions(base_objects, facts_by_id)
    ranked_objects = rank_intelligence_objects(resolved_objects, facts_by_id)
    blueprint = build_report_blueprint(ranked_objects, facts_by_id, spec, report_period_days)
    report_text = render_report_blueprint(blueprint, ranked_objects)
    metrics = build_report_metrics(
        filtered_signals_count=len(fallback_signals),
        facts=facts,
        base_object_count=len(base_objects),
        ranked_objects=ranked_objects,
        blueprint=blueprint,
    )
    metrics["cluster_inputs_count"] = len(cluster_inputs)
    metrics["cluster_fact_count"] = len(cluster_facts)
    metrics["fallback_fact_count"] = len(fallback_facts)
    return {
        "report_text": report_text,
        "facts": [fact.to_dict() for fact in facts],
        "intelligence_objects": [obj.to_dict() for obj in ranked_objects],
        "blueprint": blueprint.to_dict(),
        "metrics": metrics,
    }


def build_report_metrics(
    filtered_signals_count: int,
    facts: Sequence[NormalizedFact],
    base_object_count: int,
    ranked_objects: Sequence[IntelligenceObject],
    blueprint: ReportBlueprint,
) -> Dict[str, Any]:
    section_counts = dict(Counter(obj.draft_section for obj in ranked_objects))
    object_type_counts = dict(Counter(obj.object_type for obj in ranked_objects))
    contradiction_count = sum(1 for obj in ranked_objects if obj.contradiction_flag)
    return {
        "filtered_signals_count": filtered_signals_count,
        "normalized_facts_count": len(facts),
        "base_intelligence_objects_count": base_object_count,
        "ranked_intelligence_objects_count": len(ranked_objects),
        "contradiction_objects_count": contradiction_count,
        "executive_summary_items_count": len(blueprint.executive_summary_items),
        "key_developments_count": len(blueprint.key_development_ids),
        "appendix_references_count": len(blueprint.appendix_references),
        "section_allocations": section_counts,
        "object_type_distribution": object_type_counts,
    }
