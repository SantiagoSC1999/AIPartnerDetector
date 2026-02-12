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
        self.clarisa_countries_url = settings.CLARISA_COUNTRIES_API_URL
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

    async def fetch_clarisa_countries(self) -> List[Dict[str, Any]]:
        """Fetch countries from CLARISA API."""
        try:
            logger.info(f"Fetching countries from CLARISA: {self.clarisa_countries_url}")
            
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(
                    self.clarisa_countries_url,
                    timeout=60.0,
                    headers={"User-Agent": "CLARISA-AI-Partners/1.0"}
                )
                logger.info(f"CLARISA countries response status: {response.status_code}")
                
                response.raise_for_status()
                data = response.json()
                
                # CLARISA returns a list directly
                if isinstance(data, list):
                    logger.info(f"Got {len(data)} countries from CLARISA API")
                    return data
                else:
                    logger.error(f"Unexpected CLARISA countries response format: {type(data)}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching CLARISA countries: {str(e)}", exc_info=True)
            return []

    async def delete_all_countries(self) -> Dict[str, Any]:
        """Delete all countries from the database."""
        logger.info("Deleting all countries...")
        
        result = {
            "status": "in_progress",
            "total_deleted": 0,
            "errors": [],
        }

        try:
            response = self.supabase.client.table("countries").delete().neq("id", -1).execute()
            result["total_deleted"] = len(response.data) if response.data else 0
            logger.info(f"Deleted {result['total_deleted']} countries")
            result["status"] = "completed"
        except Exception as e:
            error_msg = f"Error deleting countries: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result["errors"].append(error_msg)
            result["status"] = "failed"

        return result

    async def delete_all_clarisa_institutions(self) -> Dict[str, Any]:
        """Delete all CLARISA institutions from the database (respects ForeignKey constraints)."""
        logger.info("Deleting all CLARISA institutions...")
        
        result = {
            "status": "in_progress",
            "total_deleted": 0,
            "errors": [],
        }

        try:
            response = self.supabase.client.table("clarisa_institutions").delete().neq("id", -1).execute()
            result["total_deleted"] = len(response.data) if response.data else 0
            logger.info(f"Deleted {result['total_deleted']} CLARISA institutions")
            result["status"] = "completed"
        except Exception as e:
            error_msg = f"Error deleting CLARISA institutions: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result["errors"].append(error_msg)
            result["status"] = "failed"

        return result

    async def reset_all_data(self) -> Dict[str, Any]:
        """Reset all CLARISA data: delete institutions first, then countries.
        
        This is a FULL RESET operation that allows you to start fresh.
        """
        logger.info("Starting full data reset...")
        
        result = {
            "status": "in_progress",
            "institutions_deleted": 0,
            "countries_deleted": 0,
            "errors": [],
        }

        try:
            # Step 1: Delete institutions first (to avoid FK constraint violations)
            logger.info("Step 1: Deleting all CLARISA institutions...")
            inst_result = await self.delete_all_clarisa_institutions()
            result["institutions_deleted"] = inst_result.get("total_deleted", 0)
            if inst_result.get("status") == "failed":
                result["errors"].extend(inst_result.get("errors", []))

            # Step 2: Delete countries
            logger.info("Step 2: Deleting all countries...")
            country_result = await self.delete_all_countries()
            result["countries_deleted"] = country_result.get("total_deleted", 0)
            if country_result.get("status") == "failed":
                result["errors"].extend(country_result.get("errors", []))

            result["status"] = "completed" if not result["errors"] else "completed_with_errors"
            logger.info(f"Data reset completed. Institutions deleted: {result['institutions_deleted']}, Countries deleted: {result['countries_deleted']}")

        except Exception as e:
            error_msg = f"Full data reset failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result["errors"].append(error_msg)
            result["status"] = "failed"

        return result

    async def delete_all_embeddings(self) -> Dict[str, Any]:
        """Delete all embeddings from the database."""
        logger.info("Deleting all embeddings...")
        
        result = {
            "status": "in_progress",
            "total_deleted": 0,
            "errors": [],
        }

        try:
            response = self.supabase.client.table("institution_embeddings").delete().neq("institution_id", -1).execute()
            result["total_deleted"] = len(response.data) if response.data else 0
            logger.info(f"Deleted {result['total_deleted']} embeddings")
            result["status"] = "completed"
        except Exception as e:
            error_msg = f"Error deleting embeddings: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result["errors"].append(error_msg)
            result["status"] = "failed"

        return result

    async def sync_countries(self) -> Dict[str, Any]:
        """Sync countries from CLARISA API to Supabase, using CLARISA 'code' as country ID.
        
        NOTE: This only INSERTS new countries. Use DELETE /institutions/delete-countries first if you want to replace all countries.
        """
        logger.info("Starting countries sync from CLARISA API...")
        
        sync_result = {
            "status": "in_progress",
            "total_fetched": 0,
            "total_saved": 0,
            "errors": [],
        }

        try:
            # Fetch countries from CLARISA API
            countries = await self.fetch_clarisa_countries()
            sync_result["total_fetched"] = len(countries)
            logger.info(f"Fetched {len(countries)} countries from CLARISA")

            if not countries:
                sync_result["status"] = "completed"
                logger.info("No countries to sync")
                return sync_result

            # Prepare countries for batch insert with CLARISA 'code' as ID
            country_records = []
            for country in countries:
                try:
                    record = {
                        "id": country.get("code"),  # Use CLARISA code as the country ID
                        "code": country.get("code"),
                        "iso_alpha2": country.get("isoAlpha2"),
                        "name": country.get("name"),
                    }
                    country_records.append(record)
                except Exception as e:
                    logger.warning(f"Error preparing country record: {str(e)}")
                    sync_result["errors"].append(str(e))

            # Batch save countries
            if country_records:
                logger.info(f"Batch saving {len(country_records)} countries...")
                try:
                    response = self.supabase.client.table("countries").insert(
                        country_records
                    ).execute()
                    sync_result["total_saved"] = len(response.data) if response.data else len(country_records)
                    logger.info(f"Batch saved {sync_result['total_saved']} countries")
                except Exception as e:
                    error_msg = f"Error batch inserting countries: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    sync_result["errors"].append(error_msg)

            sync_result["status"] = "completed"
            logger.info(f"Countries sync completed. Saved: {sync_result['total_saved']}")

        except Exception as e:
            error_msg = f"Countries sync failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            sync_result["errors"].append(error_msg)
            sync_result["status"] = "failed"

        return sync_result

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
            existing_ids = self.supabase.get_existing_clarisa_ids()
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
            country_code_to_id = self.supabase.batch_upsert_countries(list(countries_map.values()))
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
                saved_ids = self.supabase.batch_upsert_clarisa_institutions(institutions_to_save)
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


# Global instance
_sync_service: Optional[ClarisaSyncService] = None


def get_clarisa_sync_service() -> ClarisaSyncService:
    """Get or create ClarisaSyncService instance."""
    global _sync_service
    if _sync_service is None:
        _sync_service = ClarisaSyncService()
    return _sync_service

