"""
Entity classifier for distinguishing legal entities from funding programs.

Classifies institutions as:
- Legal entities: Universities, Ministries, Research Councils, NGOs
- Non-registrable entities: Funding schemes, Grant programs, Budget lines
"""

from typing import Tuple, List, Dict, Optional
from enum import Enum

from ..models.institutional_validation import EntityTypeEnum, EntityClassificationResult
from .enhanced_normalizer import EnhancedNormalizer, FundingSchemeDetector


class EntityClassifier:
    """
    Classifies institution names to detect entity types and identify funding schemes.
    
    Primary classification goals:
    1. Distinguish legal entities (universities, ministries) from funding programs
    2. Identify specific entity types (ministry, research council, etc.)
    3. Flag funding schemes that should be rejected or merged
    4. Attempt parent entity detection
    """
    
    def __init__(self):
        """Initialize classifier with pattern definitions."""
        self.normalizer = EnhancedNormalizer()
        self.funding_detector = FundingSchemeDetector()
        
        # Entity-specific patterns
        self.ministry_patterns = [
            r"ministry of",
            r"ministerio de",
            r"ministère de",
            r"ministério de",
            r"部\s*$",  # Chinese ministry
        ]
        
        self.university_patterns = [
            r"\buniversity\b",
            r"\buniversidad\b",
            r"\buniversité\b",
            r"\buniversidade\b",
            r"\b大学\b",  # Chinese university
        ]
        
        self.research_institute_patterns = [
            r"research institute",
            r"research center",
            r"research centre",
            r"institute of research",
            r"研究所",  # Chinese institute
        ]
        
        self.research_council_patterns = [
            r"research council",
            r"scientific council",
            r"national council",
            r"consejo de investigación",
            r"conseil de recherche",
            r"科学基金",  # Chinese science fund
        ]
        
        self.ngo_patterns = [
            r"\bngo\b",
            r"\bnon-governmental\b",
            r"\bnongovernmental\b",
            r"non-profit",
            r"nonprofit",
            r"\bfoundation\b",
        ]
        
        self.government_agency_patterns = [
            r"government agency",
            r"governmental agency",
            r"department of",
            r"bureau of",
            r"authority",
            r"government office",
        ]
        
        # Patterns for invalid/non-registrable entities
        self.funding_scheme_patterns = [
            r"funding scheme",
            r"research fund\b",
            r"grant program",
            r"budget line",
            r"research program\b",
            r"call for projects",
            r"internal fund",
        ]
    
    def classify_entity_type(self, text: Optional[str]) -> Tuple[EntityTypeEnum, float]:
        """
        Classify entity type from institution name.
        
        Returns top classification with confidence score.
        
        Args:
            text: Institution name
            
        Returns:
            (entity_type, confidence_0_to_1)
        """
        if not text:
            return EntityTypeEnum.UNKNOWN, 0.0
        
        norm_text = self.normalizer.normalize_text(text, remove_diacritics=False)
        norm_text_lower = norm_text.lower()
        
        # Score each entity type
        scores = {}
        
        # Check for ministry
        minister_score = self._pattern_score(norm_text_lower, self.ministry_patterns)
        scores[EntityTypeEnum.MINISTRY] = minister_score
        
        # Check for university
        university_score = self._pattern_score(norm_text_lower, self.university_patterns)
        scores[EntityTypeEnum.UNIVERSITY] = university_score
        
        # Check for research institute
        institute_score = self._pattern_score(norm_text_lower, self.research_institute_patterns)
        scores[EntityTypeEnum.RESEARCH_INSTITUTE] = institute_score
        
        # Check for research council
        council_score = self._pattern_score(norm_text_lower, self.research_council_patterns)
        scores[EntityTypeEnum.RESEARCH_COUNCIL] = council_score
        
        # Check for NGO
        ngo_score = self._pattern_score(norm_text_lower, self.ngo_patterns)
        scores[EntityTypeEnum.NGO] = ngo_score
        
        # Check for government agency
        agency_score = self._pattern_score(norm_text_lower, self.government_agency_patterns)
        scores[EntityTypeEnum.GOVERNMENT_AGENCY] = agency_score
        
        # Check for funding schemes
        funding_scheme_score = self._pattern_score(norm_text_lower, self.funding_scheme_patterns)
        scores[EntityTypeEnum.FUNDING_SCHEME] = funding_scheme_score
        
        # Apply funding scheme detector for additional signals
        is_funding, funding_conf, _ = self.funding_detector.is_funding_scheme(text)
        if is_funding:
            scores[EntityTypeEnum.FUNDING_SCHEME] = max(
                scores.get(EntityTypeEnum.FUNDING_SCHEME, 0),
                funding_conf
            )
        
        # Find highest scoring type
        if not scores or max(scores.values()) == 0:
            return EntityTypeEnum.UNKNOWN, 0.0
        
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]
        
        return best_type, min(best_score, 1.0)
    
    def classify_comprehensive(self, 
                              name: str,
                              acronym: Optional[str] = None,
                              institution_type_hint: Optional[str] = None,
                              country: Optional[str] = None) -> EntityClassificationResult:
        """
        Comprehensive entity classification with reasoning.
        
        Args:
            name: Institution name
            acronym: Institution acronym
            institution_type_hint: Type hint from source data
            country: Country name
            
        Returns:
            EntityClassificationResult with full details
        """
        detected_type, confidence = self.classify_entity_type(name)
        
        # Determine if it's a legal entity
        is_legal_entity = detected_type not in [
            EntityTypeEnum.FUNDING_SCHEME,
            EntityTypeEnum.GRANT_PROGRAM,
            EntityTypeEnum.BUDGET_LINE,
            EntityTypeEnum.RESEARCH_PROGRAM,
            EntityTypeEnum.INTERNAL_FUND,
            EntityTypeEnum.UNKNOWN,
        ]
        
        # Determine if it's a funding scheme
        is_funding_scheme = detected_type in [
            EntityTypeEnum.FUNDING_SCHEME,
            EntityTypeEnum.GRANT_PROGRAM,
            EntityTypeEnum.BUDGET_LINE,
            EntityTypeEnum.RESEARCH_PROGRAM,
            EntityTypeEnum.INTERNAL_FUND,
        ]
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            name, detected_type, confidence, is_legal_entity, is_funding_scheme
        )
        
        # Identify flags
        flags = self._identify_flags(name, detected_type, institution_type_hint)
        
        return EntityClassificationResult(
            detected_type=detected_type,
            confidence=confidence,
            reasoning=reasoning,
            is_legal_entity=is_legal_entity,
            is_funding_scheme=is_funding_scheme,
            flags=flags,
        )
    
    def _pattern_score(self, text: str, patterns: List[str]) -> float:
        """
        Score text against list of regex patterns.
        
        Returns 0.0-1.0 score based on match count.
        
        Args:
            text: Text to check
            patterns: List of regex patterns
            
        Returns:
            Score 0.0-1.0
        """
        if not text or not patterns:
            return 0.0
        
        import re
        
        matches = 0
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matches += 1
        
        # Score: more matches = higher confidence
        # Cap at 1 with 1 or more matches
        return min(1.0, matches * 0.3)
    
    def _generate_reasoning(self,
                           name: str,
                           entity_type: EntityTypeEnum,
                           confidence: float,
                           is_legal: bool,
                           is_funding: bool) -> str:
        """Generate human-readable reasoning for classification."""
        
        confidence_text = "high" if confidence >= 0.8 else "moderate" if confidence >= 0.6 else "low"
        
        if is_funding:
            return (
                f"Classified as {entity_type.value} with {confidence_text} confidence ({confidence:.2%}). "
                f"Name contains patterns indicating funding/program structure rather than a legal entity. "
                f"Should be verified for parent institution."
            )
        
        if entity_type == EntityTypeEnum.UNKNOWN:
            return (
                f"Entity type could not be determined with confidence. "
                f"Name: '{name}' does not clearly match known institutional patterns. "
                f"Require manual review or additional context."
            )
        
        return (
            f"Classified as {entity_type.value} with {confidence_text} confidence ({confidence:.2%}). "
            f"Name contains clear indicators of this entity type. Legal entity suitable for registration."
        )
    
    def _identify_flags(self,
                        name: str,
                        entity_type: EntityTypeEnum,
                        institution_type_hint: Optional[str] = None) -> List[str]:
        """Identify potential issues or concerns."""
        
        flags = []
        
        norm_name = self.normalizer.normalize_text(name, remove_diacritics=False)
        
        # Flag potential funding schemes
        if entity_type in [EntityTypeEnum.FUNDING_SCHEME, EntityTypeEnum.GRANT_PROGRAM]:
            flags.append("POTENTIAL_FUNDING_SCHEME")
        
        # Flag unknown types
        if entity_type == EntityTypeEnum.UNKNOWN:
            flags.append("UNKNOWN_TYPE_REQUIRES_REVIEW")
        
        # Flag multi-language names
        from .enhanced_normalizer import LANGUAGE_PATTERNS
        detected_langs = set()
        for lang, (_, accents) in LANGUAGE_PATTERNS.items():
            if any(accent in name for accent in accents):
                detected_langs.add(lang)
        
        if len(detected_langs) > 1:
            flags.append("MULTI_LANGUAGE_NAME")
        
        # Flag very short names
        if len(norm_name) < 10:
            flags.append("SHORT_NAME_MIGHT_BE_ACRONYM")
        
        # Flag orphaned entities (ministry vs university confusion)
        if entity_type == EntityTypeEnum.MINISTRY and "university" in norm_name.lower():
            flags.append("CONFLICTING_ENTITY_SIGNALS")
        
        # Type hint mismatch
        if institution_type_hint:
            hint_lower = institution_type_hint.lower()
            if entity_type == EntityTypeEnum.UNIVERSITY and "ministry" in hint_lower:
                flags.append("TYPE_HINT_MISMATCH")
            elif entity_type == EntityTypeEnum.MINISTRY and "university" in hint_lower:
                flags.append("TYPE_HINT_MISMATCH")
        
        return flags
    
    def detect_parent_entity(self,
                            name: str,
                            entity_classification: EntityClassificationResult) -> Optional[str]:
        """
        Attempt to detect parent entity for funding schemes.
        
        Example:
            Input: "Global Fund - Education Initiative"
            Output: "Global Fund"
        
        Args:
            name: Institution name
            entity_classification: Classification result
            
        Returns:
            Suggested parent entity name or None
        """
        if not entity_classification.is_funding_scheme:
            return None
        
        norm_name = self.normalizer.normalize_text(name, remove_diacritics=False)
        
        # Patterns for extracting parent entity
        # "X - Program" → X
        match = re.search(r"^([^-]+)\s*-\s*(?:program|fund|initiative|call)", norm_name, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # "(Program of X)" → X
        match = re.search(r"\(.*?program.*?of\s+([^)]+)\)", norm_name, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Remove known funding keywords and return remainder
        funding_keywords = r"(?:program|fund|initiative|funding|call|mechanism)\b"
        parent = re.sub(funding_keywords, "", norm_name, flags=re.IGNORECASE).strip()
        
        if parent and len(parent) > 3 and parent != norm_name:
            return parent
        
        return None


import re
