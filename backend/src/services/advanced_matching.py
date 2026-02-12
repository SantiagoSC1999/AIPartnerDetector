"""Advanced matching strategies for robust duplicate detection across 10,000+ variants."""

from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
import re
from src.services.normalization import normalize_text, normalize_acronym


# Database of common institution acronyms and their expansions
ACRONYM_DATABASE = {
    # Research Centers
    "cimmyt": ["international maize and wheat improvement center", "centro internacional de mejoramiento de maiz y trigo"],
    "icrisat": ["international crops research institute for the semi-arid tropics"],
    "irri": ["international rice research institute"],
    "ciat": ["international center for tropical agriculture", "centro internacional de agricultura tropical"],
    "icraf": ["world agroforestry centre", "international council for research in agroforestry"],
    "worldfish": ["worldfish centre", "world fish center"],
    "bioversity": ["bioversity international"],
    
    # International Organizations
    "cgiar": ["consultative group on international agricultural research"],
    "fao": ["food and agriculture organization"],
    "undp": ["united nations development programme"],
    "unep": ["united nations environment programme"],
    "icarda": ["international center for agricultural research in the dry areas"],
    
    # Universities (common patterns)
    "wur": ["wageningen university", "wageningen university and research"],
    "eth": ["swiss federal institute of technology", "eth zurich"],
    "cornell": ["cornell university"],
    "berkeley": ["university of california", "uc berkeley"],
}

# Common words and suffixes to remove for better matching

COMMON_INSTITUTION_WORDS = [
    "international", "center", "centre", "institute", "organization", "organisation",
    "foundation", "university", "college", "school", "academy", "research",
    "and research", "centre international", "research organization", "consultative",
    "council", "network", "association", "society", "board", "service",
]


def get_acronym_expansions(acronym: str) -> List[str]:
    """Get possible expansions of an acronym from the database."""
    normalized_acronym = normalize_acronym(acronym).lower()
    
    expansions = []
    for db_acronym, db_expansions in ACRONYM_DATABASE.items():
        if db_acronym in normalized_acronym or normalized_acronym in db_acronym:
            expansions.extend(db_expansions)
    
    return expansions


def fuzzy_match_score(str1: str, str2: str, threshold: float = 0.8) -> Tuple[bool, float]:
    """
    Calculate fuzzy match score using SequenceMatcher (Levenshtein-like).
    
    Returns: (is_match, score) where score is 0.0-1.0
    """
    if not str1 or not str2:
        return False, 0.0
    
    # Normalize both strings
    s1 = normalize_text(str1)
    s2 = normalize_text(str2)
    
    # Calculate similarity ratio
    matcher = SequenceMatcher(None, s1, s2)
    ratio = matcher.ratio()
    
    return ratio >= threshold, ratio


def acronym_match_score(institution_name: str, acronym: str) -> Tuple[bool, float]:
    """
    Check if acronym matches institution name.
    
    STRICT MATCHING - only return True if:
    1. Acronym appears EXPLICITLY marked (between parentheses/brackets) in the name
       AND is an EXACT MATCH of what's in parentheses
       e.g., "International Maize and Wheat Improvement Center (CIMMYT)" → acronym CIMMYT
       NOT substring matching like "gas" in "madagascar"
    2. OR acronym is in known ACRONYM_DATABASE
    3. OR acronym matches first letters perfectly
    
    DO NOT do substring matching in parentheses
    
    Returns: (is_match, confidence_score)
    """
    if not institution_name or not acronym:
        return False, 0.0
    
    normalized_name = normalize_text(institution_name)
    normalized_acronym = normalize_acronym(acronym).upper()
    
    # Strategy 1: Check if acronym appears EXPLICITLY in parentheses as EXACT MATCH
    # e.g., "(CIMMYT)" or "[CIMMYT]" - must be exact match, NOT substring
    # This prevents "GAS" matching "madagascar" where gas is a substring
    import re
    pattern = r'\(([^)]+)\)|\[([^\]]+)\]'
    matches = re.findall(pattern, normalized_name)
    for match_group in matches:
        acronym_in_parens = match_group[0] or match_group[1]
        # EXACT match only - not substring
        if normalized_acronym.lower() == acronym_in_parens.lower().strip():
            return True, 0.95
    
    # Strategy 2: Check database of known acronyms ONLY
    # This prevents false matches like TIL/GAS/etc. that aren't in the database
    expansions = get_acronym_expansions(normalized_acronym)
    if expansions:  # Only check if acronym is known in database
        for expansion in expansions:
            if fuzzy_match_score(normalized_name, expansion, threshold=0.8)[0]:
                return True, 0.92
    
    # Strategy 3: Generate acronym from first letters and compare STRICTLY
    # e.g., "National Aeronautics Space Administration" -> "NASA"
    # Only match if first letters EXACTLY match the acronym
    words = [w for w in normalized_name.split() if w]
    
    # Only try first-letter matching if we have enough words and acronym is reasonable length
    if len(words) >= 2 and len(normalized_acronym) >= 2:
        # Generate first-letter acronym
        generated_acronym = "".join(w[0].upper() for w in words if w and w[0].isalpha())
        
        # Must be EXACT match
        if generated_acronym == normalized_acronym:
            return True, 0.85
    
    # Return False for all other cases
    # IMPORTANT: This prevents TIL from matching "Tech Innovation Lab" against unrelated names
    return False, 0.0


def keyword_overlap_score(name1: str, name2: str, min_overlap: int = 2) -> Tuple[bool, float]:
    """
    Calculate score based on overlapping keywords.
    
    IMPORTANT: Only considers "meaningful" keywords (not generic institution words).
    Example:
    - "International Maize and Wheat Improvement Center" 
    - "Wheat and Maize Research Institute"
    Both have: ["wheat", "maize"] → high overlap (meaningful keywords)
    
    But:
    - "International Maize and Wheat Improvement Center"
    - "Office du Niger"
    Share generic words like ["international", "center"] but different meaningful keywords
    → Should NOT match (meaningful words don't overlap)
    
    Returns: (has_significant_overlap, overlap_score)
    """
    if not name1 or not name2:
        return False, 0.0
    
    # Extract keywords, removing ALL generic institutional words
    def extract_meaningful_keywords(text: str) -> set:
        normalized = normalize_text(text)
        words = set(normalized.split())
        
        # Remove ALL generic institutional/administrative words
        # This includes stops words AND common institution words
        stop_words = {
            "and", "or", "the", "a", "an", "of", "in", "for", "to", "is",
            "international", "center", "centre", "institute", "organization", "organisation",
            "foundation", "university", "college", "school", "academy", "research",
            "consultative", "council", "network", "association", "society", "board",
            "service", "foundation", "development", "cooperation", "programme",
        }
        
        return words - stop_words
    
    keywords1 = extract_meaningful_keywords(name1)
    keywords2 = extract_meaningful_keywords(name2)
    
    if not keywords1 or not keywords2:
        return False, 0.0
    
    overlap = keywords1 & keywords2
    overlap_count = len(overlap)
    
    if overlap_count >= min_overlap:
        # Calculate Jaccard similarity
        union = keywords1 | keywords2
        jaccard = len(overlap) / len(union)
        return True, jaccard
    
    return False, 0.0


def multi_strategy_match(
    uploaded_name: str,
    uploaded_acronym: str,
    clarisa_name: str,
    clarisa_acronym: str,
) -> Dict[str, any]:
    """
    Apply multiple matching strategies and return comprehensive scoring.
    
    IMPORTANT: Unknown acronyms (not in ACRONYM_DATABASE) are treated VERY STRICTLY.
    We only match unknown acronyms if they appear explicitly or if both names/acronyms match identically.
    
    Returns dict with:
    - match_type: "exact" | "core" | "fuzzy" | "acronym" | "keyword" | "no_match"
    - confidence: 0.0-1.0
    - signals: List of matching signals that fired
    - explanation: Human-readable explanation
    """
    
    result = {
        "match_type": "no_match",
        "confidence": 0.0,
        "signals": [],
        "explanation": "",
    }
    
    # Strategy 1: Exact match (already normalized)
    if normalize_text(uploaded_name) == normalize_text(clarisa_name):
        result["match_type"] = "exact"
        result["confidence"] = 1.0
        result["signals"].append("exact_name_match")
        result["explanation"] = "Exact institution name match"
        return result
    
    # Strategy 2: Acronym matching (STRICT - only known acronyms or explicit matches)
    # This avoids false positives like TIL matching against unrelated institutions
    if uploaded_acronym and clarisa_acronym:
        # Check if both acronyms are identical (exact acronym match)
        norm_uploaded_acr = normalize_acronym(uploaded_acronym).upper()
        norm_clarisa_acr = normalize_acronym(clarisa_acronym).upper()
        
        if norm_uploaded_acr == norm_clarisa_acr:
            # Same acronym - check if it's a known acronym or if names are similar
            if norm_uploaded_acr in [k.upper() for k in ACRONYM_DATABASE.keys()]:
                # Known acronym - verify names are reasonably similar
                fuzzy_check, fuzzy_score = fuzzy_match_score(uploaded_name, clarisa_name, threshold=0.70)
                if fuzzy_check or fuzzy_score > 0.65:
                    result["match_type"] = "acronym"
                    result["confidence"] = max(0.90, fuzzy_score)
                    result["signals"].append(f"acronym_match_{result['confidence']:.2f}")
                    result["explanation"] = f"Same acronym '{norm_uploaded_acr}' with similar names"
                    return result
            else:
                # Unknown acronym matching - be VERY STRICT
                # Only match if names are highly similar (85%+)
                if normalize_text(uploaded_name) == normalize_text(clarisa_name):
                    result["match_type"] = "acronym"
                    result["confidence"] = 0.90
                    result["signals"].append("acronym_match_exact_names")
                    result["explanation"] = "Same acronym with identical names"
                    return result
        
        # Check if uploaded acronym matches clarisa name
        acronym_match, acronym_score = acronym_match_score(clarisa_name, uploaded_acronym)
        if acronym_match:
            result["match_type"] = "acronym"
            result["confidence"] = acronym_score
            result["signals"].append(f"acronym_match_{acronym_score:.2f}")
            result["explanation"] = f"Acronym '{uploaded_acronym}' matches institution name (confidence: {acronym_score:.0%})"
            return result
        
        # Check if clarisa acronym matches uploaded name  
        acronym_match, acronym_score = acronym_match_score(uploaded_name, clarisa_acronym)
        if acronym_match:
            result["match_type"] = "acronym"
            result["confidence"] = acronym_score
            result["signals"].append(f"acronym_match_{acronym_score:.2f}")
            result["explanation"] = f"Institution matches acronym '{clarisa_acronym}' (confidence: {acronym_score:.0%})"
            return result
    
    # Strategy 3: Fuzzy matching (handles typos and variations)
    fuzzy_match, fuzzy_score = fuzzy_match_score(uploaded_name, clarisa_name, threshold=0.75)
    if fuzzy_match and fuzzy_score >= 0.85:
        result["match_type"] = "fuzzy"
        result["confidence"] = fuzzy_score
        result["signals"].append(f"fuzzy_match_{fuzzy_score:.2f}")
        result["explanation"] = f"Fuzzy match on institution name (similarity: {fuzzy_score:.0%})"
        return result
    
    # Strategy 4: Keyword overlap (good for multi-language or partial names)
    keyword_match, keyword_score = keyword_overlap_score(uploaded_name, clarisa_name, min_overlap=2)
    if keyword_match and keyword_score >= 0.70:
        result["match_type"] = "keyword"
        result["confidence"] = keyword_score
        result["signals"].append(f"keyword_match_{keyword_score:.2f}")
        result["explanation"] = f"Strong keyword overlap detected (Jaccard: {keyword_score:.0%})"
        return result
    
    # Strategy 5: Combined signals (fuzzy + keyword, but lower confidence)
    if fuzzy_score >= 0.75 or keyword_score >= 0.60:
        combined_confidence = (fuzzy_score * 0.6 + keyword_score * 0.4)
        if combined_confidence >= 0.72:
            result["match_type"] = "fuzzy"
            result["confidence"] = combined_confidence
            result["signals"].append(f"fuzzy_match_{fuzzy_score:.2f}")
            result["signals"].append(f"keyword_match_{keyword_score:.2f}")
            result["explanation"] = f"Combined fuzzy and keyword match (combined confidence: {combined_confidence:.0%})"
            return result
    
    # No match found
    result["explanation"] = "No matching signals detected"
    return result
