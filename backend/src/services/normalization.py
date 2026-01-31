"""Normalization utilities for institution data."""

import re
import unicodedata
from typing import Optional
from urllib.parse import urlparse


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
