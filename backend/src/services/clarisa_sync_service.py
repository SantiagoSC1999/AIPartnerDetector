"""Service for syncing CLARISA institutions data."""

import httpx
import asyncio
from typing import List, Dict, Any, Optional
from src.config import settings
from src.persistence.supabase_client import get_supabase_client
import logging

logger = logging.getLogger(__name__)


class ClarisaSyncService:
    """Service for fetching and syncing CLARISA institutions."""

    def __init__(self):
        """Initialize the sync service."""
        self.clarisa_url = settings.CLARISA_API_URL
        self.supabase = get_supabase_client()

    async def fetch_clarisa_institutions(self) -> List[Dict[str, Any]]:
        """Fetch institutions from CLARISA API."""
        try:
            logger.info(f"Fetching from CLARISA: {self.clarisa_url}")
            
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(
                    self.clarisa_url,
                    timeout=60.0,
                    headers={"User-Agent": "CLARISA-AI-Partners/1.0"}
                )
                logger.info(f"CLARISA response status: {response.status_code}")
                
                response.raise_for_status()
                data = response.json()
                
                logger.info(f"Response type: {type(data)}, keys: {data.keys() if isinstance(data, dict) else 'N/A'}")
                
                # CLARISA returns a list directly
                if isinstance(data, list):
                    logger.info(f"Got {len(data)} institutions directly")
                    return data
                else:
                    logger.error(f"Unexpected CLARISA response format: {type(data)}")
                    logger.error(f"Response content: {str(data)[:500]}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching CLARISA institutions: {str(e)}", exc_info=True)
            return []

    async def sync_institutions(self) -> Dict[str, Any]:
        """Sync institutions from CLARISA to Supabase with smart filtering and batch operations."""
        logger.info("Starting CLARISA institutions sync...")
        
        sync_result = {
            "status": "in_progress",
            "total_fetched": 0,
            "total_new": 0,
            "total_saved": 0,
            "errors": [],
            "countries_synced": 0,
            "note": "Embeddings are generated separately via /generate-embeddings endpoint"
        }

        try:
            # Fetch institutions from CLARISA
            institutions = await self.fetch_clarisa_institutions()
            sync_result["total_fetched"] = len(institutions)
            logger.info(f"Fetched {len(institutions)} institutions from CLARISA")

            if not institutions:
                sync_result["status"] = "completed"
                return sync_result

            # Get existing clarisa_ids to skip re-processing
            logger.info("Checking existing institutions in database...")
            existing_ids = await self.supabase.get_existing_clarisa_ids()
            logger.info(f"Found {len(existing_ids)} existing institutions")

            # Filter only NEW institutions (smart filtering)
            new_institutions = [inst for inst in institutions if inst.get("code") not in existing_ids]
            sync_result["total_new"] = len(new_institutions)
            logger.info(f"Processing {len(new_institutions)} new institutions (skipping {len(existing_ids)} existing)")

            if not new_institutions:
                sync_result["status"] = "completed"
                logger.info("No new institutions to sync")
                return sync_result

            # Extract unique countries from NEW institutions
            countries_map = {}
            for inst in new_institutions:
                if "countryOfficeDTO" in inst and inst["countryOfficeDTO"]:
                    for country in inst["countryOfficeDTO"]:
                        if country.get("isHeadquarter") == 1:
                            country_code = country.get("code")
                            if country_code and country_code not in countries_map:
                                countries_map[country_code] = country
                            break

            # BATCH save countries
            logger.info(f"Batch saving {len(countries_map)} countries...")
            country_code_to_id = await self.supabase.batch_upsert_countries(list(countries_map.values()))
            sync_result["countries_synced"] = len(country_code_to_id)
            logger.info(f"Batch saved {sync_result['countries_synced']} countries")

            # Prepare institutions for BATCH insert
            logger.info(f"Preparing {len(new_institutions)} institutions for batch insert...")
            institutions_to_save = []
            
            for institution in new_institutions:
                # Get headquarters country ID
                country_id = None
                if "countryOfficeDTO" in institution and institution["countryOfficeDTO"]:
                    for country in institution["countryOfficeDTO"]:
                        if country.get("isHeadquarter") == 1:
                            country_code = country.get("code")
                            country_id = country_code_to_id.get(country_code)
                            break

                institutions_to_save.append({
                    "institution_data": institution,
                    "country_id": country_id
                })

            # BATCH save institutions
            if institutions_to_save:
                logger.info(f"Batch saving {len(institutions_to_save)} institutions...")
                saved_ids = await self.supabase.batch_upsert_clarisa_institutions(institutions_to_save)
                sync_result["total_saved"] = len(saved_ids)
                logger.info(f"Batch saved {sync_result['total_saved']} institutions")

            sync_result["status"] = "completed"
            logger.info(
                f"Sync completed. Fetched: {sync_result['total_fetched']}, "
                f"New: {sync_result['total_new']}, Saved: {sync_result['total_saved']}"
            )

        except Exception as e:
            error_msg = f"Sync failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            sync_result["errors"].append(error_msg)
            sync_result["status"] = "failed"

        return sync_result

    def _build_embedding_text(self, institution: Dict[str, Any]) -> str:
        """Build text for embedding from institution data."""
        parts = []
        
        if institution.get("name"):
            parts.append(institution["name"])
        
        if institution.get("acronym"):
            parts.append(institution["acronym"])
        
        if institution.get("institutionType") and institution["institutionType"].get("name"):
            parts.append(institution["institutionType"]["name"])
        
        # Add headquarters country if available
        if institution.get("countryOfficeDTO"):
            for country in institution["countryOfficeDTO"]:
                if country.get("isHeadquarter") == 1 and country.get("name"):
                    parts.append(country["name"])
                    break
        
        return " ".join(parts)


# Global instance
_sync_service: Optional[ClarisaSyncService] = None


def get_clarisa_sync_service() -> ClarisaSyncService:
    """Get or create ClarisaSyncService instance."""
    global _sync_service
    if _sync_service is None:
        _sync_service = ClarisaSyncService()
    return _sync_service


# Global instance
_sync_service: Optional[ClarisaSyncService] = None


def get_clarisa_sync_service() -> ClarisaSyncService:
    """Get or create ClarisaSyncService instance."""
    global _sync_service
    if _sync_service is None:
        _sync_service = ClarisaSyncService()
    return _sync_service

