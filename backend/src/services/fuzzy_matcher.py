"""
Fuzzy matching engine for typo-tolerant institution matching.

Uses RapidFuzz for sophisticated string similarity with support for:
- Levenshtein distance
- Jaro-Winkler
- Token-based matching (handles word reordering)
- Partial matching (substring matching)
"""

from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from enum import Enum
from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein
import re

from .enhanced_normalizer import EnhancedNormalizer


class FuzzyMatchStrategy(str, Enum):
    """Different fuzzy matching strategies."""
    
    TOKEN_SET = "token_set"  # Best for word reordering
    TOKEN_SORT = "token_sort"  # Good for word order variations
    PARTIAL = "partial"  # Best for substring matching
    RATIO = "ratio"  # Standard Levenshtein
    PARTIAL_TOKEN = "partial_token"  # Combination


@dataclass
class FuzzyMatchScore:
    """Result of fuzzy matching."""
    
    score: float
    strategy: FuzzyMatchStrategy
    match_type: str
    details: str


class FuzzyMatcher:
    """
    Production-grade fuzzy matching for institution names.
    
    Handles typos, word reordering, and variations:
    - "National Science Foudnation of Chna" → matches "National Science Foundation of China"
    - "China National Science Foundation" → matches "National Science Foundation of China"
    - "NSF China" → matches "National Science Foundation China"
    """
    
    def __init__(self):
        """Initialize matcher with normalizer."""
        self.normalizer = EnhancedNormalizer()
        self.config = {
            "token_set_threshold": 0.85,
            "token_sort_threshold": 0.80,
            "partial_threshold": 0.75,
            "ratio_threshold": 0.80,
        }
    
    def fuzzy_match_ratio(self, 
                         str1: str, 
                         str2: str,
                         strategy: FuzzyMatchStrategy = FuzzyMatchStrategy.RATIO) -> FuzzyMatchScore:
        """
        Calculate fuzzy match score using specified strategy.
        
        Args:
            str1: First string
            str2: Second string
            strategy: Matching strategy to use
            
        Returns:
            FuzzyMatchScore with score and details
        """
        if not str1 or not str2:
            return FuzzyMatchScore(0.0, strategy, "empty_string", "One or both strings are empty")
        
        # Normalize both strings
        norm1 = self.normalizer.normalize_text(str1)
        norm2 = self.normalizer.normalize_text(str2)
        
        if norm1 == norm2:
            return FuzzyMatchScore(1.0, FuzzyMatchStrategy.RATIO, "exact_match", "Exact match after normalization")
        
        if strategy == FuzzyMatchStrategy.TOKEN_SET:
            score = fuzz.token_set_ratio(norm1, norm2) / 100.0
            return FuzzyMatchScore(score, strategy, "token_set", 
                                  f"Token set similarity: handles word reordering")
        
        elif strategy == FuzzyMatchStrategy.TOKEN_SORT:
            score = fuzz.token_sort_ratio(norm1, norm2) / 100.0
            return FuzzyMatchScore(score, strategy, "token_sort",
                                  f"Token sort similarity: words reordered and compared")
        
        elif strategy == FuzzyMatchStrategy.PARTIAL:
            score = fuzz.partial_ratio(norm1, norm2) / 100.0
            return FuzzyMatchScore(score, strategy, "partial",
                                  f"Partial similarity: allowing substring matches")
        
        elif strategy == FuzzyMatchStrategy.PARTIAL_TOKEN:
            score = fuzz.partial_token_set_ratio(norm1, norm2) / 100.0
            return FuzzyMatchScore(score, strategy, "partial_token",
                                  "Partial token set: substring + token matching")
        
        else:  # RATIO
            score = fuzz.ratio(norm1, norm2) / 100.0
            return FuzzyMatchScore(score, strategy, "ratio",
                                  "Standard Levenshtein distance")
    
    def multi_strategy_match(self, 
                            str1: str, 
                            str2: str,
                            weights: Optional[Dict[FuzzyMatchStrategy, float]] = None) -> Tuple[float, str]:
        """
        Use multiple strategies and combine scores.
        
        Different strategies excel at different types of variations:
        - Token set: word reordering ("China National Science Foundation")
        - Token sort: similar but stricter
        - Partial: substring matching ("National Science Foundation China")
        - Ratio: character-level matching (typos)
        
        Args:
            str1: First string
            str2: Second string
            weights: Custom weights for each strategy
            
        Returns:
            (combined_score, best_strategy_description)
        """
        if not str1 or not str2:
            return 0.0, "empty_string"
        
        # Default weights
        if weights is None:
            weights = {
                FuzzyMatchStrategy.TOKEN_SET: 0.4,  # Best for reordering
                FuzzyMatchStrategy.PARTIAL: 0.3,    # Good for substrings
                FuzzyMatchStrategy.RATIO: 0.3,      # Good for typos
            }
        
        scores = {}
        for strategy in weights.keys():
            match_result = self.fuzzy_match_ratio(str1, str2, strategy)
            scores[strategy] = match_result.score
        
        # Calculate weighted score
        combined_score = sum(
            scores[strategy] * weight 
            for strategy, weight in weights.items()
        )
        
        # Find which strategy contributed most
        best_strategy = max(scores, key=scores.get)
        
        return combined_score, best_strategy.value
    
    def match_against_registry(self,
                              query_name: str,
                              registry: List[Dict]) -> List[Tuple[Dict, float, str]]:
        """
        Match a query name against a registry of institutions.
        
        Returns top matches sorted by score.
        
        Args:
            query_name: Name to search for
            registry: List of institution dicts with 'partner_name' field
            
        Returns:
            List of (institution_dict, score, strategy) tuples, sorted by score descending
        """
        if not query_name or not registry:
            return []
        
        results = []
        
        for institution in registry:
            inst_name = institution.get("partner_name", "")
            if not inst_name:
                continue
            
            score, strategy = self.multi_strategy_match(query_name, inst_name)
            results.append((institution, score, strategy))
        
        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results
    
    def typo_correct_name(self, text: str) -> str:
        """
        Attempt to correct common typos in institution names.
        
        Uses Levenshtein distance to find close matches in common patterns.
        
        Args:
            text: Text to correct
            
        Returns:
            Corrected text or original if no correction suggested
        """
        if not text:
            return text
        
        text_lower = text.lower()
        
        # Common typo patterns and corrections
        typo_patterns = {
            # "Foudnation" → "Foundation"
            r"foudnation": "foundation",
            # "Chna" → "China"
            r"\bchna\b": "china",
            # "Sceince" → "Science"
            r"sceince": "science",
            # "Insitute" → "Institute"
            r"insitute": "institute",
            # "Univesity" → "University"
            r"univesity": "university",
            # "Councel" → "Council"
            r"councel": "council",
            # "Agnecy" → "Agency"
            r"agnecy": "agency",
            # Double letters
            r"(\w)\1{2,}": r"\1\1",  # Replace 3+ consecutive chars with 2
        }
        
        corrected = text_lower
        for pattern, replacement in typo_patterns.items():
            corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
        
        return corrected
    
    def score_name_variants(self,
                           query_name: str,
                           variant_names: List[str],
                           threshold: float = 0.7) -> List[Tuple[str, float]]:
        """
        Score query name against multiple variants.
        
        Args:
            query_name: Name to search for
            variant_names: List of variant names
            threshold: Minimum score to include in results
            
        Returns:
            List of (variant, score) tuples above threshold, sorted by score
        """
        if not query_name or not variant_names:
            return []
        
        results = []
        
        for variant in variant_names:
            if not variant:
                continue
            
            score, _ = self.multi_strategy_match(query_name, variant)
            
            if score >= threshold:
                results.append((variant, score))
        
        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results
    
    def acronym_fuzzy_match(self, 
                           acronym: str, 
                           institution_name: str) -> Tuple[bool, float]:
        """
        Check if acronym likely matches institution name.
        
        Strategies:
        1. Acronym appears in name: "CGIAR" in "Consultative Group on International Agricultural Research"
        2. First letters match: "CGIAR" from "Consultative Group International Agricultural Research"
        3. Close match: Levenshtein similarity
        
        Args:
            acronym: Acronym to check
            institution_name: Full institution name
            
        Returns:
            (matches, confidence_score)
        """
        if not acronym or not institution_name:
            return False, 0.0
        
        norm_acronym = self.normalizer.normalize_acronym(acronym)
        norm_name = self.normalizer.normalize_text(institution_name)
        
        # Strategy 1: Acronym appears in name
        if norm_acronym in norm_name.upper().replace(" ", ""):
            return True, 0.95
        
        # Strategy 2: Generate expected acronym from name
        words = norm_name.split()
        
        # Method 1: First letter of each word
        generated_acronym = "".join(w[0].upper() for w in words if w and len(w) > 1)
        if generated_acronym and norm_acronym == generated_acronym:
            return True, 0.90
        
        # Method 2: First letters of significant words (skip common words)
        common_words = {"of", "the", "and", "for", "a", "an", "in", "on", "at", "by", "de", "la", "le"}
        significant_words = [w for w in words if w and w not in common_words]
        if significant_words:
            sig_acronym = "".join(w[0].upper() for w in significant_words)
            if sig_acronym and norm_acronym == sig_acronym:
                return True, 0.85
        
        # Strategy 3: Levenshtein distance on first letters
        if len(generated_acronym) == len(norm_acronym):
            distance = Levenshtein.distance(norm_acronym, generated_acronym)
            if distance <= 1:  # Allow 1 character difference
                return True, 0.70
        
        return False, 0.0
    
    def find_best_match(self,
                       query_name: str,
                       registry: List[Dict],
                       threshold: float = 0.75) -> Optional[Tuple[Dict, float]]:
        """
        Find the single best match in registry above threshold.
        
        Args:
            query_name: Name to search for
            registry: List of institutions
            threshold: Minimum score
            
        Returns:
            (best_institution, score) or None if no match above threshold
        """
        if not query_name or not registry:
            return None
        
        matches = self.match_against_registry(query_name, registry)
        
        if matches and matches[0][1] >= threshold:
            return (matches[0][0], matches[0][1])
        
        return None
