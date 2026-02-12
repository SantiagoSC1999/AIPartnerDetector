"""
Enhanced normalizer for multi-language institutional names.

Handles Unicode normalization, diacritics removal, language detection,
and semantic synonym mapping for global institution names.
"""

import re
import unicodedata
from typing import Optional, List, Set, Dict, Tuple
from urllib.parse import urlparse, urlunparse
from functools import lru_cache


# Multi-language synonym dictionary for common institution types
INSTITUTIONAL_SYNONYMS = {
    # Ministry patterns (English, Spanish, French, Portuguese, Chinese)
    "ministry": [
        "ministerio", "ministère", "ministério", "部", "ministry",
        "department of state", "governo", "government"
    ],
    "ministry_of_education": [
        "ministry of education", "ministerio de educación", "ministère de l'éducation",
        "ministério da educação", "教育部"
    ],
    "ministry_of_science": [
        "ministry of science", "ministerio de ciencia", "ministère des sciences",
        "ministério da ciência", "科技部", "science and technology ministry"
    ],
    "national_academy": [
        "national academy", "academia nacional", "académie nationale",
        "academia nacional", "国家科学院", "academy"
    ],
    "research_council": [
        "research council", "consejo de investigación", "conseil de recherche",
        "conselho de pesquisa", "研究委员会"
    ],
    "university": [
        "university", "universidad", "université", "universidade", "大学", "college"
    ],
    "institute": [
        "institute", "instituto", "institut", "instituto", "研究所",
        "institution", "institución", "institution"
    ]
}

# Common prefixes that should be removed for matching
INSTITUTION_PREFIXES_TO_REMOVE = [
    r"^the\s+",
    r"^peoples\s+republic\s+of\s+",
    r"^republic\s+of\s+",
    r"^kingdom\s+of\s+",
]

# Common suffixes for branch/regional entities
BRANCH_INDICATORS = [
    r"\s*-\s*\w+\s*$",  # "-Bangladesh", "-Africa"
    r"\s*\(\s*\w+\s*\)\s*$",  # "(USA)", "(China)"
    r"\s+branch\s*$",
    r"\s+regional\s+office\s*$",
    r"\s+country\s+office\s*$",
]

# Keyword patterns for funding program detection
FUNDING_SCHEME_KEYWORDS = {
    "program": r"\bprogram(me)?\b",
    "fund": r"\bfund(s)?\b",
    "funding_scheme": r"\bfunding\s+scheme\b",
    "research_fund": r"\bresearch\s+fund\b",
    "grant": r"\bgrant(s)?\b",
    "initiative": r"\binitiative(s)?\b",
    "call": r"\bcall\s+for\s+projects\b",
    "mechanism": r"\bmechanism(s)?\b",
    "facility": r"\bfacility\b",
}

# Language detection patterns (simplified - can use lingua for more accuracy)
LANGUAGE_PATTERNS = {
    "spanish": (r"\b(de|el|la|los|las|y)\b", ["ción", "ñ", "á", "é", "í", "ó", "ú"]),
    "french": (r"\b(le|la|les|de|du|et)\b", ["ç", "é", "è", "ê", "ë", "à"]),
    "portuguese": (r"\b(de|o|a|os|as|e)\b", ["ão", "õ", "ç", "é", "á"]),
}


class EnhancedNormalizer:
    """
    Production-grade normalizer for institutional names.
    
    Supports:
    - Unicode normalization (NFD)
    - Diacritics removal
    - Multi-language text handling
    - URL normalization
    - Acronym extraction
    - Language detection
    """
    
    def __init__(self):
        """Initialize normalizer with caching."""
        # Language-specific patterns will be compiled on first use
        self._language_patterns_compiled = {}
    
    @staticmethod
    @lru_cache(maxsize=10000)
    def normalize_text(text: Optional[str], remove_diacritics: bool = True) -> str:
        """
        Normalize text with Unicode NFD decomposition.
        
        Args:
            text: Text to normalize
            remove_diacritics: Whether to remove accents/diacritics
            
        Returns:
            Normalized text (lowercase, trimmed, NFD-decomposed)
        """
        if not text:
            return ""
        
        # Convert to lowercase and trim
        text = str(text).lower().strip()
        
        # Apply Unicode normalization (NFD form)
        # This decomposes characters like é into e + ´
        text = unicodedata.normalize("NFD", text)
        
        # Remove diacritical marks if requested
        if remove_diacritics:
            text = "".join(
                char for char in text 
                if unicodedata.category(char) != "Mn"  # Mn = Mark, Nonspacing
            )
        
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text).strip()
        
        # Remove leading/trailing punctuation
        text = re.sub(r"^[\s\-\.,;:]*|[\s\-\.,;:]*$", "", text)
        
        return text
    
    @staticmethod
    @lru_cache(maxsize=10000)
    def normalize_acronym(text: Optional[str]) -> str:
        """
        Normalize acronym by removing periods and spaces.
        
        Args:
            text: Acronym text
            
        Returns:
            Normalized acronym (uppercase, no periods)
        """
        if not text:
            return ""
        
        text = str(text).upper().strip()
        text = re.sub(r"[\s\.\-]+", "", text)
        return text
    
    @staticmethod
    def normalize_url(url: Optional[str]) -> str:
        """
        Normalize URLs for comparison.
        
        Handles:
        - Protocol normalization (http → https)
        - www prefix normalization
        - Trailing slash removal
        - Domain lowercasing
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL
        """
        if not url:
            return ""
        
        url = str(url).strip().lower()
        
        # Add scheme if missing
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        # Normalize scheme to https
        url = url.replace("http://", "https://")
        
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            
            # Remove www prefix if present
            if netloc.startswith("www."):
                netloc = netloc[4:]
            
            # Remove www. prefix variations
            netloc = re.sub(r"^www\d*\.", "", netloc)
            
            # Reconstruct URL without path, query, fragment
            normalized = urlunparse((parsed.scheme, netloc, "", "", "", ""))
            
            # Remove trailing slash
            normalized = normalized.rstrip("/")
            
            return normalized
        except Exception:
            return ""
    
    def extract_core_name(self, text: Optional[str]) -> str:
        """
        Extract core institution name by removing:
        - Regional/branch indicators (e.g., "-Bangladesh")
        - Common suffixes (e.g., "Limited", "Institute")
        
        Example:
            "Plan International-Bangladesh" → "plan international"
            "National Science Foundation Limited" → "national science foundation"
        
        Args:
            text: Full institution name
            
        Returns:
            Core institution name
        """
        if not text:
            return ""
        
        text = self.normalize_text(text)
        
        # Remove branch indicators first
        for pattern in BRANCH_INDICATORS:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
        
        # Remove common institutional suffixes
        suffixes_pattern = r"\b(ltd|limited|inc|incorporated|llc|llp|lp|co|corp|corporation|sa|gmbh|ag|bv|nv|foundation|institute|university|college|school|academy|center|centre|association|society|organization|organisation|bureau|agency|department|ministry|authority|board|service|office|division|branch)\b"
        text = re.sub(suffixes_pattern, "", text, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"^[\s\-,\.;:]*|[\s\-,\.;:]*$", "", text)
        
        return text
    
    def get_name_variants(self, text: Optional[str]) -> Set[str]:
        """
        Generate name variants for matching.
        
        Returns different normalized representations:
        - Full normalized name
        - Core name (without suffixes)
        - Without special characters
        - Abbreviated (first letters)
        
        Args:
            text: Institution name
            
        Returns:
            Set of name variants
        """
        if not text:
            return set()
        
        variants = set()
        
        # Variant 1: Full normalized
        normalized = self.normalize_text(text)
        if normalized:
            variants.add(normalized)
        
        # Variant 2: Core name
        core = self.extract_core_name(text)
        if core and core != normalized:
            variants.add(core)
        
        # Variant 3: Without special characters
        no_special = re.sub(r"[^\w\s]", "", normalized)
        if no_special and len(no_special) > 2:
            variants.add(no_special)
        
        # Variant 4: Abbreviated (first letters of each word)
        words = normalized.split()
        if len(words) > 1 and all(len(w) > 0 for w in words):
            abbreviated = "".join(w[0] for w in words)
            if len(abbreviated) > 1:
                variants.add(abbreviated)
        
        # Variant 5: Without common prefixes
        for prefix_pattern in INSTITUTION_PREFIXES_TO_REMOVE:
            variant = re.sub(prefix_pattern, "", normalized, flags=re.IGNORECASE)
            if variant and variant != normalized and len(variant) > 2:
                variants.add(variant.strip())
        
        return {v for v in variants if v and len(v) > 1}
    
    def extract_acronym(self, text: Optional[str]) -> Optional[str]:
        """
        Extract acronym from institution name.
        
        Looks for:
        1. Text already in parentheses: "University of X (UX)"
        2. All-caps words: "CGIAR"
        3. First letters of key words
        
        Args:
            text: Institution name
            
        Returns:
            Extracted acronym or None
        """
        if not text:
            return None
        
        text = str(text).strip()
        
        # Pattern 1: Explicitly marked acronym in parentheses
        match = re.search(r'\(([A-Z]{2,})\)', text)
        if match:
            return match.group(1)
        
        # Pattern 2: All-caps words (e.g., "CGIAR", "UNESCO")
        all_caps_words = re.findall(r'\b[A-Z]{2,}\b', text)
        if all_caps_words:
            # Return the first one that looks like an acronym
            return all_caps_words[0]
        
        # Pattern 3: Generate from first letters (fallback)
        words = text.split()
        if len(words) <= 5:  # Only for shorter names
            # Take first letter of each significant word
            acronym_letters = []
            for word in words:
                if word and len(word) > 1 and not word.lower() in ["of", "the", "and", "for", "de", "del", "la", "le"]:
                    acronym_letters.append(word[0].upper())
            
            if 2 <= len(acronym_letters) <= 5:
                return "".join(acronym_letters)
        
        return None
    
    def detect_language(self, text: Optional[str]) -> str:
        """
        Detect language of institution name (simplified version).
        
        Args:
            text: Text to analyze
            
        Returns:
            Language code (e.g., "en", "es", "fr") or "unknown"
        """
        if not text:
            return "unknown"
        
        text_lower = text.lower()
        
        # Check for non-ASCII patterns indicating specific languages
        for lang, (keywords, accents) in LANGUAGE_PATTERNS.items():
            # Check for language-specific characters
            if any(accent in text for accent in accents):
                return lang
            
            # Check for keyword matches
            if re.search(keywords, text_lower):
                # Verify it's actually that language with accent marks
                if any(accent in text for accent in accents):
                    return lang
        
        return "en"  # Default to English
    
    def resolve_synonym(self, text: Optional[str], synonym_category: str) -> Optional[str]:
        """
        Resolve text to canonical synonym form.
        
        Example:
            resolve_synonym("Ministerio de Educación", "ministry_of_education")
            → "ministry of education"
        
        Args:
            text: Text to match
            synonym_category: Category key from INSTITUTIONAL_SYNONYMS
            
        Returns:
            Canonical form or None if no match
        """
        if not text or synonym_category not in INSTITUTIONAL_SYNONYMS:
            return None
        
        normalized = self.normalize_text(text)
        
        # Check if text matches any synonym in the category
        for synonym in INSTITUTIONAL_SYNONYMS[synonym_category]:
            if self.normalize_text(synonym) == normalized:
                # Return the first (canonical) form
                return INSTITUTIONAL_SYNONYMS[synonym_category][0]
        
        return None
    
    def build_embedding_text(self, 
                            name: str, 
                            acronym: Optional[str] = None,
                            institution_type: Optional[str] = None,
                            country: Optional[str] = None) -> str:
        """
        Build combined text for embedding generation.
        
        Concatenates institution metadata for semantic similarity search.
        
        Args:
            name: Institution name
            acronym: Acronym
            institution_type: Type classification
            country: Country name
            
        Returns:
            Combined text for embedding
        """
        parts = [name]
        
        if acronym:
            parts.append(acronym)
        
        if institution_type:
            parts.append(institution_type)
        
        if country:
            parts.append(country)
        
        combined = " ".join(str(p).strip() for p in parts if p)
        return self.normalize_text(combined, remove_diacritics=False)


class FundingSchemeDetector:
    """Specialized detector for funding schemes vs legal entities."""
    
    @staticmethod
    def is_funding_scheme(text: Optional[str]) -> Tuple[bool, float, List[str]]:
        """
        Detect if institution name represents a funding scheme/program.
        
        Returns:
            (is_scheme, confidence, matched_keywords)
        """
        if not text:
            return False, 0.0, []
        
        text_lower = str(text).lower()
        matched_keywords = []
        
        # Count keyword matches
        for keyword, pattern in FUNDING_SCHEME_KEYWORDS.items():
            if re.search(pattern, text_lower):
                matched_keywords.append(keyword)
        
        # Calculate confidence based on matches
        if not matched_keywords:
            return False, 0.0, []
        
        # More keywords = higher confidence
        confidence = min(1.0, len(matched_keywords) * 0.25)
        
        # Exact phrase patterns are high confidence
        exact_patterns = [
            r"funding scheme",
            r"grant program",
            r"research fund",
            r"call for projects"
        ]
        
        if any(re.search(p, text_lower) for p in exact_patterns):
            confidence = 0.95
        
        is_scheme = confidence >= 0.60
        
        return is_scheme, confidence, matched_keywords
