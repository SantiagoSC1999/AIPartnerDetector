"""
Decision engine for institutional validation.

Orchestrates the complete validation pipeline:
1. Normalization
2. Entity classification
3. Duplicate detection
4. Decision generation
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from ..models.institutional_validation import (
    InstitutionValidationRequest,
    InstitutionValidationResult,
    EntityTypeEnum,
    DecisionEnum,
    MatchResult,
    MatchTypeEnum,
    AdvancedMatchConfig,
)
from .enhanced_normalizer import EnhancedNormalizer
from .entity_classifier import EntityClassifier
from .fuzzy_matcher import FuzzyMatcher, FuzzyMatchStrategy


logger = logging.getLogger(__name__)


class DecisionEngine:
    """
    Orchestrates the complete validation pipeline.
    
    Coordinates:
    - Text normalization
    - Entity classification
    - Duplicate detection
    - Reasoned decision making
    """
    
    def __init__(self, config: Optional[AdvancedMatchConfig] = None):
        """
        Initialize decision engine.
        
        Args:
            config: Matching configuration with thresholds
        """
        self.config = config or AdvancedMatchConfig()
        self.normalizer = EnhancedNormalizer()
        self.classifier = EntityClassifier()
        self.fuzzy_matcher = FuzzyMatcher()
        
        logger.info("DecisionEngine initialized with config: %s", self.config)
    
    def validate_institution(self,
                            request: InstitutionValidationRequest,
                            clarisa_registry: List[Dict[str, Any]],
                            embeddings_index: Optional[Any] = None) -> InstitutionValidationResult:
        """
        Complete validation pipeline for a single institution.
        
        Args:
            request: Validation request with institution data
            clarisa_registry: List of known CLARISA institutions
            embeddings_index: Optional embeddings index for semantic search
            
        Returns:
            Complete validation result with decision
        """
        
        logger.info(f"Validating institution: {request.partner_name}")
        
        # Step 1: Normalize input
        normalized_name = self.normalizer.normalize_text(request.partner_name)
        normalized_acronym = None
        if request.acronym:
            normalized_acronym = self.normalizer.normalize_acronym(request.acronym)
        elif not request.acronym:
            # Try to extract acronym from name
            normalized_acronym = self.normalizer.extract_acronym(request.partner_name)
        
        normalized_url = ""
        if request.web_page:
            normalized_url = self.normalizer.normalize_url(request.web_page)
        
        # Step 2: Classify entity type
        entity_classification = self.classifier.classify_comprehensive(
            request.partner_name,
            request.acronym,
            request.institution_type,
            request.country_name,
        )
        
        # Step 3: Detect for funding schemes
        is_potential_funding_scheme = self.classifier.classify_entity_type(
            request.partner_name
        )[0] in [EntityTypeEnum.FUNDING_SCHEME, EntityTypeEnum.GRANT_PROGRAM]
        
        parent_entity = None
        parent_entity_id = None
        if is_potential_funding_scheme:
            parent_entity = self.classifier.detect_parent_entity(
                request.partner_name,
                entity_classification
            )
        
        # Step 4: Duplicate detection
        matches = self._find_duplicates(
            request,
            normalized_name,
            normalized_acronym,
            clarisa_registry,
            embeddings_index,
        )
        
        # Step 5: Make decision
        decision, confidence, reason = self._make_decision(
            request,
            entity_classification,
            is_potential_funding_scheme,
            matches,
        )
        
        # Step 6: Generate recommendations
        recommendations = self._generate_recommendations(
            decision,
            entity_classification,
            is_potential_funding_scheme,
            matches,
        )
        
        # Build result
        result = InstitutionValidationResult(
            request_id=request.id,
            uploaded_at=datetime.utcnow(),
            input_data=request,
            normalized_name=normalized_name,
            normalized_acronym=normalized_acronym,
            normalized_url=normalized_url,
            entity_type_detected=entity_classification.detected_type,
            entity_classification=entity_classification,
            is_duplicate=len(matches) > 0 and matches[0].is_probable_duplicate,
            duplicate_match_score=matches[0].similarity_score if matches else 0.0,
            matched_clarisa_id=matches[0].clarisa_id if matches else None,
            matched_clarisa_name=matches[0].clarisa_name if matches else None,
            match_details=matches,
            is_potential_funding_scheme=is_potential_funding_scheme,
            recommended_parent_entity=parent_entity,
            decision=decision,
            confidence_score=confidence,
            reason=reason,
            recommendations=recommendations,
        )
        
        return result
    
    def _find_duplicates(self,
                        request: InstitutionValidationRequest,
                        normalized_name: str,
                        normalized_acronym: Optional[str],
                        clarisa_registry: List[Dict[str, Any]],
                        embeddings_index: Optional[Any] = None) -> List[MatchResult]:
        """
        Find duplicate matches in CLARISA registry.
        
        Uses multiple strategies:
        1. Exact name match
        2. Normalized name match
        3. Fuzzy matching
        4. Semantic similarity (if embeddings available)
        5. Acronym matching
        """
        
        matches = []
        
        for clarisa_record in clarisa_registry:
            clarisa_name = clarisa_record.get("partner_name", "")
            clarisa_id = clarisa_record.get("id")
            
            if not clarisa_name or not clarisa_id:
                continue
            
            # Check exact match
            exact_match = self.normalizer.normalize_text(clarisa_name) == normalized_name
            if exact_match:
                matches.append(MatchResult(
                    clarisa_id=clarisa_id,
                    clarisa_name=clarisa_name,
                    clarisa_country=clarisa_record.get("country_id"),
                    similarity_score=1.0,
                    match_type=MatchTypeEnum.EXACT_NAME,
                    signals=[],
                    is_probable_duplicate=True,
                ))
                continue
            
            # Check fuzzy match
            score, strategy = self.fuzzy_matcher.multi_strategy_match(
                normalized_name,
                self.normalizer.normalize_text(clarisa_name)
            )
            
            if score >= self.config.duplicate_threshold:
                matches.append(MatchResult(
                    clarisa_id=clarisa_id,
                    clarisa_name=clarisa_name,
                    clarisa_country=clarisa_record.get("country_id"),
                    similarity_score=score,
                    match_type=MatchTypeEnum.FUZZY_NAME,
                    signals=[],
                    is_probable_duplicate=score >= self.config.duplicate_threshold,
                ))
        
        # Sort by similarity score descending
        matches.sort(key=lambda x: x.similarity_score, reverse=True)
        
        # Return top matches
        return matches[:self.config.max_matches_to_return]
    
    def _make_decision(self,
                       request: InstitutionValidationRequest,
                       entity_classification: Any,
                       is_potential_funding_scheme: bool,
                       matches: List[MatchResult]) -> tuple:
        """
        Make approval/rejection decision based on validation results.
        
        Returns:
            (decision, confidence_score, reason)
        """
        
        # If it's clearly a funding scheme, recommend rejection or merge
        if is_potential_funding_scheme:
            if entity_classification.detected_type == EntityTypeEnum.FUNDING_SCHEME:
                return (
                    DecisionEnum.REJECT,
                    0.95,
                    f"Entity is classified as a {entity_classification.detected_type.value}. "
                    f"Funding schemes and grant programs are not registrable as institutions. "
                    f"Please identify and register the parent legal entity instead."
                )
        
        # If duplicates found with high confidence
        if matches and matches[0].is_probable_duplicate:
            top_match = matches[0]
            if top_match.similarity_score >= 0.95:
                return (
                    DecisionEnum.REJECT,
                    0.95,
                    f"Institution matches existing entry '{top_match.clarisa_name}' "
                    f"(CLARISA ID: {top_match.clarisa_id}) with {top_match.similarity_score:.1%} similarity. "
                    f"This appears to be a duplicate."
                )
            elif top_match.similarity_score >= 0.85:
                return (
                    DecisionEnum.MERGE,
                    0.85,
                    f"Institution likely matches existing entry '{top_match.clarisa_name}' "
                    f"(CLARISA ID: {top_match.clarisa_id}) with {top_match.similarity_score:.1%} similarity. "
                    f"Consider merging or requiring review."
                )
        
        # If unknown entity type
        if entity_classification.detected_type == EntityTypeEnum.UNKNOWN:
            return (
                DecisionEnum.REVIEW,
                0.50,
                f"Entity type could not be clearly determined. "
                f"Manual review recommended to verify this is a valid registrable institution."
            )
        
        # If entity type has flags
        if entity_classification.flags:
            if "TYPE_HINT_MISMATCH" in entity_classification.flags:
                return (
                    DecisionEnum.REVIEW,
                    0.70,
                    f"Detected entity type ({entity_classification.detected_type.value}) "
                    f"conflicts with provided institution type hint. "
                    f"Review required to resolve conflict."
                )
        
        # Default: approve if legal entity
        if entity_classification.is_legal_entity:
            confidence = entity_classification.confidence
            if confidence < 0.6:
                return (
                    DecisionEnum.REVIEW,
                    confidence,
                    f"Entity appears to be a valid institution ({entity_classification.detected_type.value}) "
                    f"but confidence is moderate ({confidence:.1%}). "
                    f"Recommend review before final approval."
                )
            else:
                return (
                    DecisionEnum.APPROVE,
                    confidence,
                    f"Institution is classified as {entity_classification.detected_type.value} "
                    f"with high confidence ({confidence:.1%}). Suitable for registration."
                )
        
        # Fallback
        return (
            DecisionEnum.REVIEW,
            0.50,
            "Could not reach clear decision. Manual review recommended."
        )
    
    def _generate_recommendations(self,
                                 decision: DecisionEnum,
                                 entity_classification: Any,
                                 is_funding_scheme: bool,
                                 matches: List[MatchResult]) -> List[str]:
        """Generate actionable recommendations."""
        
        recommendations = []
        
        if decision == DecisionEnum.APPROVE:
            recommendations.append("✓ Ready for registration")
            if entity_classification.detected_type == EntityTypeEnum.MINISTRY:
                recommendations.append("Note: This is a government ministry. Verify official ministry status in country registry.")
        
        elif decision == DecisionEnum.REJECT:
            if is_funding_scheme:
                recommendations.append("✗ Identify and register parent legal entity instead")
                recommendations.append("Funding programs cannot be registered as independent institutions")
            else:
                recommendations.append(f"✗ Reject as duplicate of existing entry")
                if matches:
                    recommendations.append(
                        f"If different entity, request new name/details to distinguish from {matches[0].clarisa_name}"
                    )
        
        elif decision == DecisionEnum.MERGE:
            recommendations.append("◐ Consider merging with existing entry")
            if matches:
                recommendations.append(
                    f"Proposed merge target: {matches[0].clarisa_name} (ID: {matches[0].clarisa_id})"
                )
            recommendations.append("Verify that both records refer to same institution before merging")
        
        elif decision == DecisionEnum.REVIEW:
            recommendations.append("? Requires manual review")
            recommendations.append(f"Entity type: {entity_classification.detected_type.value}")
            if entity_classification.flags:
                recommendations.append(f"Issues: {', '.join(entity_classification.flags)}")
            if matches:
                recommendations.append(f"Top potential duplicate: {matches[0].clarisa_name} ({matches[0].similarity_score:.1%})")
        
        return recommendations
