"""Duplicate detection logic and classification."""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from src.services.normalization import (
    normalize_text,
    normalize_url,
    normalize_acronym,
    build_embedding_text,
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
    exact_acronym_match: bool = False
    exact_url_match: bool = False
    semantic_name_similarity: float = 0.0
    semantic_combined_similarity: float = 0.0
    same_country: bool = False


class DuplicateDetector:
    """Service for detecting duplicate institutions."""

    def __init__(self):
        """Initialize detector."""
        self.exact_threshold = settings.EXACT_MATCH_THRESHOLD
        self.duplicate_threshold = settings.DUPLICATE_THRESHOLD
        self.potential_duplicate_threshold = settings.POTENTIAL_DUPLICATE_THRESHOLD

    def check_exact_name_match(
        self, uploaded_record: Dict[str, Any], clarisa_record: Dict[str, Any]
    ) -> bool:
        """
        Check for EXACT name match ONLY.
        
        Rule 1: Normalize and compare ONLY institution names.
        Do NOT consider country, institution_type, or website.
        """
        uploaded_name = normalize_text(uploaded_record.get("partner_name", ""))
        clarisa_name = normalize_text(clarisa_record.get("partner_name", ""))
        
        return bool(uploaded_name and clarisa_name and uploaded_name == clarisa_name)

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
        
        Rule 3: If no exact name match, use semantic similarity on NAME ONLY.
        Rule 4: Semantic matches are POSSIBLE_DUPLICATE, not hard duplicates.
        Rule 5: Website comparison is optional and secondary.
        Rule 6: Country is context only, never a hard rule.
        
        Returns: (signals, is_candidate) where is_candidate means this is a possible match.
        """
        signals = DetectionSignals()

        # Rule 6: Country is context, check it but don't use as hard filter
        countries_match = str(uploaded_record.get("country_id")).lower() == str(
            clarisa_record.get("country_id")).lower()
        signals.same_country = countries_match
        
        # Rule 3: Use semantic similarity threshold for semantic matching
        # Threshold for considering it a possible duplicate
        semantic_threshold = 0.75  # Configurable
        
        if combined_similarity >= semantic_threshold:
            signals.semantic_combined_similarity = combined_similarity
            return signals, True
        
        # Rule 5: Optional website check (secondary)
        url1 = normalize_url(uploaded_record.get("web_page"))
        url2 = normalize_url(clarisa_record.get("web_page"))
        if url1 and url2 and url1 == url2:
            signals.exact_url_match = True
            # Website match is a strong supporting signal
            return signals, True

        return signals, False

    def classify_record(
        self,
        uploaded_record: Dict[str, Any],
        similarity_results: Optional[Dict[str, Any]] = None,
    ) -> Tuple[DuplicateStatus, float, str, Optional[int]]:
        """
        Classify an uploaded record as DUPLICATE, POSSIBLE_DUPLICATE, or NO_MATCH.

        Rule 1: Exact name match → DUPLICATE (similarity = 1.0)
        Rule 4: Semantic similarity → POSSIBLE_DUPLICATE
        Rule 7: Always provide explainable reason

        Returns:
            Tuple of (status, similarity_score, reason, matched_clarisa_id)
        """

        # If no similarity results, it's a no_match
        if not similarity_results:
            return DuplicateStatus.NO_MATCH, 0.0, "No matching institutions found", None

        similarity_score = similarity_results.get("similarity_score", 0.0)
        matched_clarisa_id = similarity_results.get("matched_clarisa_id")
        signals = similarity_results.get("signals", DetectionSignals())

        # Rule 1: Exact name match = DUPLICATE (highest priority)
        if signals.exact_name_match:
            reason = "Exact name match"
            return DuplicateStatus.DUPLICATE, 1.0, reason, matched_clarisa_id

        # Rule 4: Semantic similarity = POSSIBLE_DUPLICATE
        if similarity_score >= 0.75:  # Semantic threshold
            reason = self._build_semantic_reason(signals, similarity_score)
            return (
                DuplicateStatus.POSSIBLE_DUPLICATE,
                similarity_score,
                reason,
                matched_clarisa_id,
            )

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

        if not reasons:
            reasons.append("high semantic similarity")

        return "Semantic similarity - " + ", ".join(reasons)


def get_duplicate_detector() -> DuplicateDetector:
    """Get duplicate detector instance."""
    return DuplicateDetector()
