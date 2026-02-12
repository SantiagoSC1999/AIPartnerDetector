"""Service for generating and managing embeddings."""

import logging
from typing import List, Dict, Any, Optional
from src.persistence.supabase_client import get_supabase_client
from src.embeddings.bedrock_service import get_embeddings_service

logger = logging.getLogger(__name__)


class EmbeddingGenerationService:
    """Service for generating embeddings for institutions."""

    def __init__(self):
        """Initialize the embedding service."""
        self.supabase = get_supabase_client()
        self.bedrock = get_embeddings_service()

    def generate_missing_embeddings(self) -> Dict[str, Any]:
        """Generate embeddings for institutions that don't have them yet."""
        result = {
            "status": "in_progress",
            "total_institutions": 0,
            "embeddings_generated": 0,
            "errors": [],
        }

        try:
            logger.info("Starting embedding generation for institutions without embeddings...")
            
            # Get institutions without embeddings
            institutions = self.supabase.get_institutions_without_embeddings()
            result["total_institutions"] = len(institutions)
            logger.info(f"Found {len(institutions)} institutions without embeddings")

            if not institutions:
                result["status"] = "completed"
                logger.info("All institutions already have embeddings")
                return result

            # Debug: Log the first institution to see structure
            logger.info(f"First institution structure: {institutions[0] if institutions else 'NONE'}")

            # Generate embeddings for each institution
            for idx, institution in enumerate(institutions):
                try:
                    # Build embedding text with proper format
                    embedding_text = self._build_embedding_text(institution)
                    logger.info(f"Institution {institution.get('clarisa_id')}: Generated embedding text: '{embedding_text}'")
                    
                    # Generate embedding vector
                    embedding_vector = self.bedrock.generate_embedding(embedding_text)
                    
                    if embedding_vector:
                        # Save embedding using 'id' (the primary key) as institution_id
                        # This matches the foreign key constraint in institution_embeddings
                        inst_id = institution.get("id")
                        self.supabase.upsert_institution_embedding(
                            institution_id=inst_id,  # Use local 'id' as the foreign key
                            embedding_text=embedding_text,
                            embedding_vector=embedding_vector,
                        )
                        result["embeddings_generated"] += 1
                        
                        if (idx + 1) % 100 == 0:
                            logger.info(f"Generated {idx + 1}/{len(institutions)} embeddings")
                    else:
                        error_msg = f"Failed to generate embedding for institution {institution.get('id')}"
                        logger.warning(error_msg)
                        result["errors"].append(error_msg)

                except Exception as e:
                    error_msg = f"Error generating embedding for institution {institution.get('id')}: {str(e)}"
                    logger.error(error_msg)
                    result["errors"].append(error_msg)

            result["status"] = "completed"
            logger.info(
                f"Embedding generation completed. "
                f"Generated: {result['embeddings_generated']}/{result['total_institutions']}"
            )

        except Exception as e:
            error_msg = f"Embedding generation failed: {str(e)}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
            result["status"] = "failed"

        return result

    def _build_embedding_text(self, institution: Dict[str, Any]) -> str:
        """Build text for embedding from institution data.
        
        Format: acronym: {acronym}, Partner_name: {institution_name}, institution_type: {institution_type}, website: {website}, country: {country_name}
        """
        parts = []
        
        if institution.get("acronym"):
            parts.append(f"acronym: {institution['acronym']}")
        
        if institution.get("name"):
            parts.append(f"Partner_name: {institution['name']}")
        
        if institution.get("institution_type"):
            parts.append(f"institution_type: {institution['institution_type']}")
        
        if institution.get("website"):
            parts.append(f"website: {institution['website']}")
        
        # Resolve country name - try country_name first, fall back to countries_map if needed
        country_name = institution.get("country_name")
        if not country_name and institution.get("country_id"):
            # If country_name is not present, try to resolve from supabase
            try:
                countries_map = self.supabase.get_countries_map()
                country_name = countries_map.get(institution.get("country_id"))
                logger.debug(f"Resolved country_id {institution.get('country_id')} to: {country_name}")
            except Exception as e:
                logger.warning(f"Could not resolve country for {institution.get('clarisa_id')}: {str(e)}")
        
        if country_name:
            parts.append(f"country: {country_name}")
        else:
            logger.warning(f"No country_name for institution {institution.get('clarisa_id')} (country_id: {institution.get('country_id')})")
        
        embedding_text = ", ".join(parts) if parts else ""
        logger.debug(f"Built embedding text for {institution.get('clarisa_id')}: {embedding_text[:100]}...")
        return embedding_text


# Global instance
_embedding_service: Optional[EmbeddingGenerationService] = None


def get_embedding_generation_service() -> EmbeddingGenerationService:
    """Get or create EmbeddingGenerationService instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingGenerationService()
    return _embedding_service
