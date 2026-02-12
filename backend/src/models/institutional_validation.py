"""Pydantic models for institutional validation and duplicate detection."""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


class EntityTypeEnum(str, Enum):
    """Detected entity type classification."""
    
    MINISTRY = "ministry"
    UNIVERSITY = "university"
    RESEARCH_COUNCIL = "research_council"
    RESEARCH_INSTITUTE = "research_institute"
    NGO = "ngo"
    GOVERNMENT_AGENCY = "government_agency"
    FUNDING_SCHEME = "funding_scheme"
    GRANT_PROGRAM = "grant_program"
    BUDGET_LINE = "budget_line"
    RESEARCH_PROGRAM = "research_program"
    INTERNAL_FUND = "internal_fund"
    UNKNOWN = "unknown"


class DecisionEnum(str, Enum):
    """Validation decision outcomes."""
    
    APPROVE = "approve"
    REJECT = "reject"
    MERGE = "merge"
    REVIEW = "review"


class MatchTypeEnum(str, Enum):
    """Types of matches detected."""
    
    EXACT_NAME = "exact_name"
    NORMALIZED_NAME = "normalized_name"
    CORE_NAME = "core_name"
    FUZZY_NAME = "fuzzy_name"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    ACRONYM_MATCH = "acronym_match"
    EXACT_URL = "exact_url"
    SAME_COUNTRY_NAME = "same_country_name"


class MatchSignal(BaseModel):
    """Individual match signal."""
    
    match_type: MatchTypeEnum
    score: float = Field(ge=0.0, le=1.0)
    confidence: str = Field(description="low, medium, high")
    details: Optional[str] = None


class MatchResult(BaseModel):
    """Result of matching an uploaded institution against CLARISA."""
    
    clarisa_id: int
    clarisa_name: str
    clarisa_country: Optional[str] = None
    similarity_score: float = Field(ge=0.0, le=1.0)
    match_type: MatchTypeEnum
    signals: List[MatchSignal]
    is_probable_duplicate: bool


class EntityClassificationResult(BaseModel):
    """Result of entity type classification."""
    
    detected_type: EntityTypeEnum
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    is_legal_entity: bool
    is_funding_scheme: bool
    flags: List[str] = Field(default_factory=list)
    
    class Config:
        use_enum_values = False


class InstitutionValidationRequest(BaseModel):
    """Validation request for an institution record."""
    
    id: str
    partner_name: str
    acronym: Optional[str] = None
    web_page: Optional[str] = None
    institution_type: Optional[str] = None
    country_id: Optional[str] = None
    country_name: Optional[str] = None
    additional_context: Optional[Dict[str, Any]] = None


class InstitutionValidationResult(BaseModel):
    """Complete validation result for an institution."""
    
    # Input information
    request_id: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    input_data: InstitutionValidationRequest
    
    # Normalization results
    normalized_name: str
    normalized_acronym: Optional[str] = None
    normalized_url: Optional[str] = None
    
    # Entity classification
    entity_type_detected: EntityTypeEnum
    entity_classification: EntityClassificationResult
    
    # Duplicate detection
    is_duplicate: bool
    duplicate_match_score: float = Field(ge=0.0, le=1.0)
    matched_clarisa_id: Optional[int] = None
    matched_clarisa_name: Optional[str] = None
    match_details: Optional[List[MatchResult]] = Field(default_factory=list)
    
    # Parent entity detection (for funding schemes)
    is_potential_funding_scheme: bool = False
    recommended_parent_entity: Optional[str] = None
    parent_entity_clarisa_id: Optional[int] = None
    
    # Decision and reasoning
    decision: DecisionEnum
    confidence_score: float = Field(ge=0.0, le=1.0)
    reason: str
    recommendations: List[str] = Field(default_factory=list)
    
    # Audit trail
    processing_notes: List[str] = Field(default_factory=list)


class ValidationBatchResponse(BaseModel):
    """Response for batch validation."""
    
    batch_id: str
    total_records: int
    processed: int
    approved: int
    rejected: int
    review_required: int
    merge_candidates: int
    results: List[InstitutionValidationResult]
    processing_time_seconds: float
    errors: List[Dict[str, Any]] = Field(default_factory=list)


class AdvancedMatchConfig(BaseModel):
    """Configuration for matching thresholds and behavior."""
    
    exact_match_threshold: float = 1.0
    fuzzy_match_threshold: float = 0.85
    semantic_match_threshold: float = 0.80
    potential_duplicate_threshold: float = 0.75
    duplicate_threshold: float = 0.85
    
    # Language detection
    detect_language: bool = True
    normalize_language_variants: bool = True
    
    # Funding scheme detection
    detect_funding_schemes: bool = True
    funding_scheme_confidence_threshold: float = 0.70
    
    # Parent entity detection
    detect_parent_entities: bool = True
    
    # Performance
    max_matches_to_return: int = 5
    use_index_search: bool = True
    
    @validator('*', pre=True)
    def validate_thresholds(cls, v):
        """Ensure thresholds are between 0 and 1."""
        if isinstance(v, float):
            if not 0.0 <= v <= 1.0:
                raise ValueError('Threshold values must be between 0.0 and 1.0')
        return v
