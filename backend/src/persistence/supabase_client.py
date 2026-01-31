"""Supabase client for database operations."""

from typing import Dict, List, Any, Optional
import logging
from src.config import settings
import json

logger = logging.getLogger(__name__)

try:
    import supabase
except ImportError:
    logger.warning("Supabase not available, using mock mode")
    supabase = None


class SupabaseClient:
    """Client for Supabase operations."""

    def __init__(self):
        """Initialize Supabase client."""
        self.use_mock = settings.USE_MOCK_SUPABASE
        
        if not self.use_mock and supabase:
            try:
                self.client = supabase.create_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_KEY
                )
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing Supabase: {str(e)}")
                self.use_mock = True
                self.client = None
        else:
            self.client = None

    async def upsert_country(self, country_data: Dict[str, Any]) -> Optional[int]:
        """Upsert a country into the countries table."""
        if self.use_mock:
            # Mock: return a deterministic ID based on country code
            return country_data.get("code")

        try:
            country_record = {
                "code": country_data.get("code"),
                "iso_alpha2": country_data.get("isoAlpha2"),
                "name": country_data.get("name"),
            }

            response = self.client.table("countries").upsert(
                country_record,
                on_conflict="iso_alpha2"
            ).execute()

            if response.data:
                return response.data[0]["id"]
            return None

        except Exception as e:
            logger.error(f"Error upserting country: {str(e)}")
            return None

    async def upsert_clarisa_institution(
        self,
        institution_data: Dict[str, Any],
        country_id: Optional[int] = None
    ) -> Optional[int]:
        """Upsert a CLARISA institution into the clarisa_institutions table."""
        if self.use_mock:
            # Mock: return a deterministic ID based on clarisa_id
            return institution_data.get("code")

        try:
            institution_record = {
                "clarisa_id": institution_data.get("code"),
                "name": institution_data.get("name"),
                "acronym": institution_data.get("acronym"),
                "website": institution_data.get("websiteLink"),
                "institution_type": institution_data.get("institutionType", {}).get("name"),
                "country_id": country_id,
            }

            response = self.client.table("clarisa_institutions").upsert(
                institution_record,
                on_conflict="clarisa_id"
            ).execute()

            if response.data:
                return response.data[0]["id"]
            return None

        except Exception as e:
            logger.error(f"Error upserting institution: {str(e)}")
            return None

    async def upsert_institution_embedding(
        self,
        institution_id: int,
        embedding_text: str,
        embedding_vector: List[float],
    ) -> Optional[int]:
        """Upsert an institution embedding into the institution_embeddings table.
        
        Note: institution_id should be the clarisa_id from clarisa_institutions table.
        """
        if self.use_mock:
            # Mock: return a deterministic ID
            return institution_id

        try:
            embedding_record = {
                "institution_id": institution_id,
                "embedding_text": embedding_text,
                "embedding_vector": embedding_vector,
            }

            response = self.client.table("institution_embeddings").upsert(
                embedding_record,
                on_conflict="institution_id"
            ).execute()

            if response.data:
                return response.data[0]["id"]
            return None

        except Exception as e:
            logger.error(f"Error upserting embedding: {str(e)}")
            return None

    async def get_institutions_count(self) -> int:
        """Get total count of institutions."""
        if self.use_mock:
            return 0

        try:
            response = self.client.table("clarisa_institutions").select(
                "count", count="exact"
            ).execute()
            return response.count or 0
        except Exception as e:
            logger.error(f"Error getting institutions count: {str(e)}")
            return 0

    async def get_countries_count(self) -> int:
        """Get total count of countries."""
        if self.use_mock:
            return 0

        try:
            response = self.client.table("countries").select(
                "count", count="exact"
            ).execute()
            return response.count or 0
        except Exception as e:
            logger.error(f"Error getting countries count: {str(e)}")
            return 0

    async def get_embeddings_count(self) -> int:
        """Get total count of embeddings."""
        if self.use_mock:
            return 0

        try:
            response = self.client.table("institution_embeddings").select(
                "count", count="exact"
            ).execute()
            return response.count or 0
        except Exception as e:
            logger.error(f"Error getting embeddings count: {str(e)}")
            return 0

    async def get_clarisa_institutions(self) -> List[Dict[str, Any]]:
        """Get all CLARISA institutions WITH their pre-generated embeddings for duplicate detection.
        
        Uses batch pagination to fetch all 10k+ institutions and embeddings.
        """
        if self.use_mock:
            return []

        try:
            batch_size = 1000
            offset = 0
            all_institutions = []
            
            # Fetch ALL institutions in batches (Supabase PostgREST limit is 1000 per request)
            logger.info("Fetching all CLARISA institutions in batches...")
            while True:
                institutions_response = self.client.table("clarisa_institutions").select(
                    "id, clarisa_id, name, acronym, institution_type, website, country_id, countries(name)"
                ).order("id").offset(offset).limit(batch_size).execute()
                
                batch = institutions_response.data or []
                if not batch:
                    break
                    
                all_institutions.extend(batch)
                logger.info(f"Fetched batch: {len(batch)} institutions (total so far: {len(all_institutions)})")
                
                if len(batch) < batch_size:
                    break
                    
                offset += batch_size
            
            logger.info(f"Total institutions fetched: {len(all_institutions)}")
            
            # Fetch ALL embeddings in batches
            logger.info("Fetching all embeddings in batches...")
            offset = 0
            all_embeddings = []
            
            while True:
                embeddings_response = self.client.table("institution_embeddings").select(
                    "institution_id, embedding_vector"
                ).order("institution_id").offset(offset).limit(batch_size).execute()
                
                batch = embeddings_response.data or []
                if not batch:
                    break
                    
                all_embeddings.extend(batch)
                logger.info(f"Fetched embeddings batch: {len(batch)} (total so far: {len(all_embeddings)})")
                
                if len(batch) < batch_size:
                    break
                    
                offset += batch_size
            
            logger.info(f"Total embeddings fetched: {len(all_embeddings)}")
            
            # Create a mapping of institution_id -> embedding_vector
            embedding_map = {
                item["institution_id"]: item["embedding_vector"] 
                for item in all_embeddings
            }
            
            logger.info(f"Loaded {len(embedding_map)} embeddings for CLARISA institutions")
            
            # Merge institutions with their embeddings, but only include those with embedding
            institutions = []
            for inst in all_institutions:
                embedding = embedding_map.get(inst.get("id"))
                if embedding is not None:
                    country_name = None
                    if inst.get("countries") and isinstance(inst["countries"], dict):
                        country_name = inst["countries"].get("name")
                    institutions.append({
                        "id": inst.get("id"),
                        "clarisa_id": inst.get("clarisa_id"),
                        "partner_name": inst.get("name"),
                        "acronym": inst.get("acronym") or "",
                        "institution_type": inst.get("institution_type"),
                        "web_page": inst.get("website") or "",
                        "country_id": inst.get("country_id"),
                        "country_name": country_name,
                        "embedding_vector": embedding,  # Add pre-generated embedding
                    })
            logger.info(f"Fetched {len(institutions)} CLARISA institutions with embeddings for duplicate detection")
            return institutions
        except Exception as e:
            logger.error(f"Error getting CLARISA institutions: {str(e)}", exc_info=True)
            return []

    async def get_institutions_without_embeddings(self) -> List[Dict[str, Any]]:
        """Get institutions that don't have embeddings yet.
        
        This efficiently finds all institutions that don't have embeddings
        by comparing the full institutions table with the embeddings table.
        """
        if self.use_mock:
            return []

        try:
            logger.info("Fetching all institutions...")
            
            # Fetch ALL institutions in batches (Supabase limit is 1000 per request)
            all_institutions = []
            batch_size = 1000
            offset = 0
            
            while True:
                response = self.client.table("clarisa_institutions").select(
                    "id, clarisa_id, name, acronym, institution_type, website, country_id, countries(name)"
                ).order("id").offset(offset).limit(batch_size).execute()
                
                batch = response.data or []
                if not batch:
                    break
                
                all_institutions.extend(batch)
                logger.info(f"Fetched batch: {len(batch)} institutions (total so far: {len(all_institutions)})")
                
                if len(batch) < batch_size:
                    break
                
                offset += batch_size
            
            logger.info(f"Total institutions fetched: {len(all_institutions)}")
            
            if not all_institutions:
                return []
            
            # Fetch ALL embeddings in batches
            logger.info("Fetching all embeddings...")
            all_embeddings = []
            offset = 0
            
            while True:
                response = self.client.table("institution_embeddings").select(
                    "institution_id"
                ).order("institution_id").offset(offset).limit(batch_size).execute()
                
                batch = response.data or []
                if not batch:
                    break
                
                all_embeddings.extend(batch)
                logger.info(f"Fetched embeddings batch: {len(batch)} (total so far: {len(all_embeddings)})")
                
                if len(batch) < batch_size:
                    break
                
                offset += batch_size
            
            logger.info(f"Total embeddings fetched: {len(all_embeddings)}")
            
            # Extract institution_ids that have embeddings (stored as local 'id' values)
            inst_ids_with_embeddings = {item["institution_id"] for item in all_embeddings}
            
            # Filter institutions without embeddings - use 'id' for matching (the primary key)
            institutions_without_embeddings = []
            for inst in all_institutions:
                institution_id = inst.get("id")  # Use the local 'id' primary key
                
                # Only add if this institution's id is NOT in embeddings
                if institution_id and institution_id not in inst_ids_with_embeddings:
                    country_name = None
                    if inst.get("countries") and isinstance(inst["countries"], dict):
                        country_name = inst["countries"].get("name")
                    
                    institutions_without_embeddings.append({
                        "id": institution_id,  # This goes into institution_embeddings.institution_id
                        "clarisa_id": inst.get("clarisa_id"),  # For reference only
                        "name": inst.get("name"),
                        "acronym": inst.get("acronym"),
                        "institution_type": inst.get("institution_type"),
                        "website": inst.get("website", ""),
                        "country_id": inst.get("country_id"),
                        "country_name": country_name,
                    })
            
            logger.info(f"Found {len(institutions_without_embeddings)} institutions without embeddings")
            logger.info(f"Need to generate: {len(institutions_without_embeddings)} embeddings")
            
            return institutions_without_embeddings
            
        except Exception as e:
            logger.error(f"Error getting institutions without embeddings: {str(e)}", exc_info=True)
            return []

    async def batch_upsert_countries(self, countries: List[Dict[str, Any]]) -> Dict[int, int]:
        """Batch upsert countries and return mapping of country_code -> id."""
        if self.use_mock:
            return {c.get("code"): c.get("code") for c in countries}

        try:
            country_records = [
                {
                    "code": c.get("code"),
                    "iso_alpha2": c.get("isoAlpha2"),
                    "name": c.get("name"),
                }
                for c in countries
            ]

            response = self.client.table("countries").upsert(
                country_records,
                on_conflict="iso_alpha2"
            ).execute()

            # Build mapping of code -> id
            country_code_to_id = {}
            if response.data:
                for item in response.data:
                    country_code_to_id[item.get("code")] = item.get("id")
            
            logger.info(f"Batch saved {len(country_code_to_id)} countries")
            return country_code_to_id

        except Exception as e:
            logger.error(f"Error batch upserting countries: {str(e)}")
            return {}

    async def batch_upsert_clarisa_institutions(
        self,
        institutions_data: List[Dict[str, Any]]
    ) -> List[int]:
        """Batch upsert CLARISA institutions and return list of IDs."""
        if self.use_mock:
            return [inst["institution_data"].get("code") for inst in institutions_data]

        try:
            institution_records = [
                {
                    "clarisa_id": inst["institution_data"].get("code"),
                    "name": inst["institution_data"].get("name"),
                    "acronym": inst["institution_data"].get("acronym"),
                    "website": inst["institution_data"].get("websiteLink"),
                    "institution_type": inst["institution_data"].get("institutionType", {}).get("name"),
                    "country_id": inst["country_id"],
                }
                for inst in institutions_data
            ]

            response = self.client.table("clarisa_institutions").upsert(
                institution_records,
                on_conflict="clarisa_id"
            ).execute()

            # Extract IDs
            saved_ids = []
            if response.data:
                saved_ids = [item.get("id") for item in response.data if item.get("id")]
            
            logger.info(f"Batch saved {len(saved_ids)} institutions")
            return saved_ids

        except Exception as e:
            logger.error(f"Error batch upserting institutions: {str(e)}")
            return []

    async def get_existing_clarisa_ids(self) -> set:
        """Get set of existing clarisa_ids for smart filtering."""
        if self.use_mock:
            return set()

        try:
            response = self.client.table("clarisa_institutions").select("clarisa_id").execute()
            return {inst["clarisa_id"] for inst in response.data or []}
        except Exception as e:
            logger.error(f"Error getting existing clarisa_ids: {str(e)}")
            return set()

    async def batch_upsert_embeddings(
        self,
        embeddings_data: List[Dict[str, Any]],
        embeddings_service
    ) -> int:
        """Batch upsert embeddings with vector generation."""
        if self.use_mock:
            return len(embeddings_data)

        try:
            # Generate all embeddings
            embedding_records = []
            
            for i, emb_data in enumerate(embeddings_data):
                try:
                    embedding_vector = await embeddings_service.generate_embedding(
                        emb_data["embedding_text"]
                    )
                    
                    if embedding_vector:
                        embedding_records.append({
                            "institution_id": emb_data["institution_id"],
                            "embedding_text": emb_data["embedding_text"],
                            "embedding_vector": embedding_vector,
                        })
                except Exception as e:
                    logger.warning(f"Error generating embedding for {emb_data['institution_id']}: {str(e)}")
                
                if (i + 1) % 100 == 0:
                    logger.info(f"Generated {i + 1}/{len(embeddings_data)} embeddings")

            # Batch insert embeddings
            if embedding_records:
                response = self.client.table("institution_embeddings").upsert(
                    embedding_records,
                    on_conflict="institution_id"
                ).execute()
                
                saved_count = len(response.data) if response.data else 0
                logger.info(f"Batch saved {saved_count} embeddings")
                return saved_count
            
            return 0

        except Exception as e:
            logger.error(f"Error batch upserting embeddings: {str(e)}")
            return 0
    async def save_analysis_records(
        self,
        file_id: str,
        filename: str,
        total_records: int,
        results: List[Dict[str, Any]]
    ) -> bool:
        """Save analysis results to the database."""
        if self.use_mock:
            return True

        try:
            # Save each result record
            records_to_save = []
            for result in results:
                record = {
                    "file_id": file_id,
                    "filename": filename,
                    "uploaded_id": result.get("id"),
                    "institution_name": result.get("institution_name", ""),
                    "acronym": result.get("acronym"),
                    "status": result.get("status"),
                    "similarity": result.get("similarity", 0),
                    "clarisa_match": result.get("clarisa_match"),
                    "reason": result.get("reason", ""),
                    "web_page": result.get("web_page"),
                    "type": result.get("type", ""),
                    "country": result.get("country"),
                    "created_at": "now()",  # Will be handled by Supabase
                }
                records_to_save.append(record)
            
            # Batch insert all records
            if records_to_save:
                response = self.client.table("analysis_records").insert(records_to_save).execute()
                logger.info(f"Saved {len(records_to_save)} analysis records for file {file_id}")
                return True
            
            return False

        except Exception as e:
            logger.error(f"Error saving analysis records: {str(e)}", exc_info=True)
            return False

    async def get_analysis_list(self) -> List[Dict[str, Any]]:
        """Get list of all analyses with summary info."""
        if self.use_mock:
            return []

        try:
            # Get all analysis records ordered by creation date
            response = self.client.table("analysis_records").select(
                "file_id, filename, created_at"
            ).order("created_at", desc=True).execute()
            
            # Group by file_id to get unique analyses
            analyses = {}
            for record in response.data or []:
                file_id = record.get("file_id")
                if file_id and file_id not in analyses:
                    analyses[file_id] = {
                        "file_id": file_id,
                        "filename": record.get("filename"),
                        "created_at": record.get("created_at"),
                    }
            
            logger.info(f"Retrieved {len(analyses)} unique analyses")
            return list(analyses.values())

        except Exception as e:
            logger.error(f"Error getting analysis list: {str(e)}", exc_info=True)
            return []

    async def get_analysis_details(self, file_id: str) -> Dict[str, Any]:
        """Get detailed analysis results for a specific file."""
        if self.use_mock:
            return {}

        try:
            # First get all analysis records for this file
            response = self.client.table("analysis_records").select("*").eq(
                "file_id", file_id
            ).order("uploaded_id").execute()
            
            if not response.data:
                return {"error": "Analysis not found"}
            
            records = response.data
            filename = records[0].get("filename") if records else ""
            created_at = records[0].get("created_at") if records else ""
            
            # Get unique country IDs from records
            country_ids = set()
            for record in records:
                country = record.get("country")
                if country:
                    country_ids.add(country)
            
            # Fetch country names
            country_map = {}
            if country_ids:
                countries_response = self.client.table("countries").select(
                    "id, name"
                ).in_("id", list(country_ids)).execute()
                
                for country in countries_response.data or []:
                    country_map[country.get("id")] = country.get("name")
            
            # Enrich records with country names
            for record in records:
                country_id = record.get("country")
                if country_id and country_id in country_map:
                    record["country_name"] = country_map[country_id]
                else:
                    record["country_name"] = None
            
            # Count by status
            status_counts = {
                "duplicate": 0,
                "possible_duplicate": 0,
                "no_match": 0,
            }
            
            for record in records:
                status = record.get("status", "no_match")
                if status in status_counts:
                    status_counts[status] += 1
            
            return {
                "file_id": file_id,
                "filename": filename,
                "created_at": created_at,
                "total_records": len(records),
                "summary": status_counts,
                "records": records,
            }

        except Exception as e:
            logger.error(f"Error getting analysis details: {str(e)}", exc_info=True)
            return {"error": str(e)}

# Global instance
_supabase_client: Optional[SupabaseClient] = None


def get_supabase_client() -> SupabaseClient:
    """Get or create Supabase client."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client
