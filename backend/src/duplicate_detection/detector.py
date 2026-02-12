"""Duplicate detection logic and classification."""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from src.services.normalization import (
    normalize_text,
    normalize_url,
    normalize_acronym,
    extract_core_name,
    get_name_variants,
)
from src.services.advanced_matching import (
    multi_strategy_match,
    acronym_match_score,
    fuzzy_match_score,
    keyword_overlap_score,
)
from src.config import settings


class DuplicateStatus(str, Enum):
    """Classification status for institutions."""

    DUPLICATE = "duplicate"
    POTENTIAL_DUPLICATE = "potential_duplicate"
    NO_MATCH = "no_match"


@dataclass
class DetectionSignals:
    """Signals that triggered duplicate detection."""

    exact_name_match: bool = False
    core_name_match: bool = False
    variant_name_match: bool = False
    exact_acronym_match: bool = False
    exact_url_match: bool = False
    semantic_name_similarity: float = 0.0
    semantic_combined_similarity: float = 0.0
    same_country: bool = False
    acronym_similarity: float = 0.0
    keyword_match_score: float = 0.0


class DuplicateDetector:
    """Service for detecting duplicate institutions."""

    def __init__(self):
        """Initialize detector."""
        self.exact_threshold = settings.EXACT_MATCH_THRESHOLD
        self.duplicate_threshold = settings.DUPLICATE_THRESHOLD
        self.potential_duplicate_threshold = settings.POTENTIAL_DUPLICATE_THRESHOLD


    
    def advanced_multi_strategy_match(
        self, uploaded_record: Dict[str, Any], clarisa_record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply all matching strategies and return comprehensive result.
        """
        return multi_strategy_match(
            uploaded_name=uploaded_record.get("partner_name", ""),
            uploaded_acronym=uploaded_record.get("acronym", ""),
            clarisa_name=clarisa_record.get("partner_name", ""),
            clarisa_acronym=clarisa_record.get("acronym", ""),
        )

    def check_semantic_similarity(
        self,
        embedding_uploaded: Optional[List[float]],
        embedding_clarisa: Optional[List[float]],
        name_uploaded_embedding: Optional[List[float]],
        name_clarisa_embedding: Optional[List[float]],
        similarity_func,
    ) -> Tuple[float, float]:
        """Calculate semantic similarity scores."""
        combined_similarity = 0.0
        name_similarity = 0.0

        if embedding_uploaded and embedding_clarisa:
            combined_similarity = similarity_func(embedding_uploaded, embedding_clarisa)

        if name_uploaded_embedding and name_clarisa_embedding:
            name_similarity = similarity_func(name_uploaded_embedding, name_clarisa_embedding)

        return combined_similarity, name_similarity

    def check_rule_based_signals(
        self,
        uploaded_record: Dict[str, Any],
        clarisa_record: Dict[str, Any],
        combined_similarity: float,
    ) -> Tuple[DetectionSignals, bool]:
        """
        Apply rule-based signals for semantic matching.
        
        Returns: (signals, is_candidate) where is_candidate means this is a possible match.
        """
        signals = DetectionSignals()

        # Country context
        countries_match = str(uploaded_record.get("country_id")).lower() == str(
            clarisa_record.get("country_id")).lower()
        signals.same_country = countries_match
        
        # Rule 3: Use semantic similarity threshold for semantic matching
        # Lowered threshold to catch more variants
        semantic_threshold = 0.70  # More aggressive to catch variants
        
        if combined_similarity >= semantic_threshold:
            signals.semantic_combined_similarity = combined_similarity
            return signals, True
        
        # Rule 5: Optional website check (secondary)
        url1 = normalize_url(uploaded_record.get("web_page"))
        url2 = normalize_url(clarisa_record.get("web_page"))
        if url1 and url2 and url1 == url2:
            signals.exact_url_match = True
            return signals, True

        return signals, False

    def classify_record(
        self,
        uploaded_record: Dict[str, Any],
        similarity_results: Optional[Dict[str, Any]] = None,
    ) -> Tuple[DuplicateStatus, float, str, Optional[int]]:
        """
        Classify an uploaded record as DUPLICATE, POSSIBLE_DUPLICATE, or NO_MATCH.

        Returns:
            Tuple of (status, similarity_score, reason, matched_clarisa_id)
        """

        # If no similarity results, it's a no_match
        if not similarity_results:
            return DuplicateStatus.NO_MATCH, 0.0, "No matching institutions found", None

        similarity_score = similarity_results.get("similarity_score", 0.0)
        matched_clarisa_id = similarity_results.get("matched_clarisa_id")
        signals = similarity_results.get("signals", DetectionSignals())
        match_type = similarity_results.get("match_type", "unknown")
        explanation = similarity_results.get("explanation", "")

        # TIER 1: Exact matches = DUPLICATE
        if signals.exact_name_match or signals.core_name_match or signals.variant_name_match:
            return DuplicateStatus.DUPLICATE, max(similarity_score, 0.95), explanation or "Exact name match", matched_clarisa_id
        
        # TIER 2: Strong acronym matches = DUPLICATE (very important for 10K+ variants)
        if signals.acronym_similarity >= 0.90:
            reason = f"Acronym match with {similarity_score:.0%} confidence"
            return DuplicateStatus.DUPLICATE, similarity_score, reason, matched_clarisa_id
        
        # TIER 3: Fuzzy + keyword matches = POSSIBLE_DUPLICATE
        if similarity_score >= 0.85:
            return DuplicateStatus.DUPLICATE, similarity_score, explanation or f"Strong match ({similarity_score:.0%})", matched_clarisa_id
        
        # TIER 4: Good semantic matches = POSSIBLE_DUPLICATE
        if similarity_score >= 0.72:
            reason = explanation or self._build_semantic_reason(signals, similarity_score)
            return DuplicateStatus.POSSIBLE_DUPLICATE, similarity_score, reason, matched_clarisa_id
        
        # TIER 5: Moderate acronym + website = POSSIBLE_DUPLICATE
        if signals.exact_url_match and signals.acronym_similarity > 0.7:
            reason = f"Website match with acronym similarity ({signals.acronym_similarity:.0%})"
            return DuplicateStatus.POSSIBLE_DUPLICATE, max(signals.acronym_similarity, 0.75), reason, matched_clarisa_id
        
        # No match
        return DuplicateStatus.NO_MATCH, 0.0, "No matching institutions found", None

    def _build_semantic_reason(self, signals: DetectionSignals, similarity_score: float) -> str:
        """Build explanation for semantic match."""
        reasons = []

        if signals.exact_url_match:
            reasons.append("website match")
        
        if signals.semantic_combined_similarity > 0.0:
            reasons.append(f"semantic similarity ({similarity_score:.2f})")
        
        if signals.same_country:
            reasons.append("same country")
        
        if signals.keyword_match_score > 0.0:
            reasons.append(f"keyword match ({signals.keyword_match_score:.2f})")

        if not reasons:
            reasons.append("high semantic similarity")

        return "Semantic similarity - " + ", ".join(reasons)


def get_duplicate_detector() -> DuplicateDetector:
    """Get duplicate detector instance."""
    return DuplicateDetector()
