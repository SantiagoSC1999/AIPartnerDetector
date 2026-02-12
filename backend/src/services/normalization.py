"""Normalization utilities for institution data."""

import re
import unicodedata
from typing import Optional
from urllib.parse import urlparse


# Common institution suffixes and prefixes to normalize
INSTITUTION_SUFFIXES = [
    r'\b(ltd|limited|inc|incorporated|llc|llp|lp|co\.|corp|corporation|sa|gmbh|ag|bv|nv)\b',
    r'\b(foundation|institute|university|college|school|academy|center|centre|association|society|organization|bureau|agency|department|ministry|authority|board|service|office|division|branch)\b',
    r'\b(and|&|plus)\s+(partners?|associates?|consultants?|enterprises?|solutions?)\b',
]

# Country and region suffixes
LOCATION_SUFFIXES = [
    r'-\s*\w+\s*$',  # Matches "-Bangladesh", "-Africa", "-Asia", etc.
    r'\s*\(\s*\w+\s*\)\s*$',  # Matches "(Bangladesh)", "(Africa)", etc.
]


def normalize_text(text: Optional[str]) -> str:
    """Normalize text by lowercasing, trimming, and removing accents."""
    if not text:
        return ""

    # Convert to lowercase
    text = text.lower().strip()

    # Remove accents
    nfd_form = unicodedata.normalize("NFD", text)
    text = "".join(char for char in nfd_form if unicodedata.category(char) != "Mn")

    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text)

    return text


def extract_core_name(text: Optional[str]) -> str:
    """
    Extract core institution name by removing common suffixes and location identifiers.
    
    This helps match "Plan International" with "Plan International-Bangladesh"
    by extracting just "plan international" from both.
    """
    if not text:
        return ""
    
    text = normalize_text(text)
    
    # Remove location suffixes like "-Bangladesh", "(USA)", etc.
    for pattern in LOCATION_SUFFIXES:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    
    # Remove common institutional suffixes
    for pattern in INSTITUTION_SUFFIXES:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    
    # Clean up extra whitespace and punctuation
    text = re.sub(r"[\s\-,\.;:]+$", "", text)  # Remove trailing punctuation
    text = re.sub(r"\s+", " ", text).strip()
    
    return text


def get_name_variants(text: Optional[str]) -> list:
    """
    Generate name variants for fuzzy matching.
    
    Returns different representations of the same institution name
    to improve matching in cases like "Plan International" variants.
    """
    if not text:
        return []
    
    variants = set()
    
    # Add original normalized
    normalized = normalize_text(text)
    variants.add(normalized)
    
    # Add core name (without suffixes)
    core = extract_core_name(text)
    if core and core != normalized:
        variants.add(core)
    
    # Add without special characters
    no_special = re.sub(r"[^\w\s]", "", normalized)
    if no_special and no_special != normalized:
        variants.add(no_special)
    
    # Add abbreviated versions (first letter of each word)
    words = normalized.split()
    if len(words) > 1:
        abbreviated = "".join(w[0] for w in words if w)
        variants.add(abbreviated)
    
    return list(variants)


def normalize_url(url: Optional[str]) -> str:
    """Normalize URL by standardizing format."""
    if not url:
        return ""

    url = url.strip().lower()

    # Remove trailing slashes
    url = url.rstrip("/")

    # Add protocol if missing
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Normalize protocol (prefer https)
    url = url.replace("http://", "https://")

    # Normalize www
    url = re.sub(r"https://www\.", "https://", url)
    if "https://" in url and "www." not in url:
        url = url.replace("https://", "https://www.", 1)
        # Actually, let's keep it simple - just remove www
        url = url.replace("https://www.", "https://")

    return url


def normalize_acronym(acronym: Optional[str]) -> str:
    """Normalize acronym by uppercasing and removing special chars."""
    if not acronym:
        return ""

    # Remove special characters, keep only alphanumeric
    acronym = re.sub(r"[^a-z0-9]", "", acronym.lower())

    return acronym


def build_embedding_text(
    partner_name: str, acronym: str, institution_type: str, country_id: str
) -> str:
    """Build combined text for embedding generation with specific format.
    
    Format: acronym: {acronym}, Partner_name: {institution_name}, institution_type: {Institution_type_id}, website: {website}, country: {country_id}
    """
    # Build in the exact format requested with acronym first
    parts = []
    
    if acronym:
        parts.append(f"acronym: {acronym}")
    
    if partner_name:
        parts.append(f"Partner_name: {partner_name}")
    
    if institution_type:
        parts.append(f"institution_type: {institution_type}")
    
    if country_id:
        parts.append(f"country: {country_id}")
    
    return ", ".join(parts)
