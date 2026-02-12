"""Main API router for institutions duplicate detection."""

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Optional
import uuid
import json

from src.services.excel_parser import parse_excel_file, ExcelParsingError
from src.services.clarisa_sync_service import get_clarisa_sync_service
from src.embeddings.bedrock_service import get_embeddings_service
from src.duplicate_detection.detector import get_duplicate_detector, DuplicateStatus, DetectionSignals
from src.persistence.supabase_client import get_supabase_client
from src.audit.logger import get_audit_logger
from src.config import settings

router = APIRouter(prefix="/institutions", tags=["institutions"])

# Mock CLARISA institutions for testing (since we can't always connect to the API)
MOCK_CLARISA_INSTITUTIONS = [
    {
        "id": 1,
        "partner_name": "International Maize and Wheat Improvement Center",
        "acronym": "CIMMYT",
        "web_page": "https://www.cimmyt.org",
        "institution_type": "Research Center",
        "country_id": "MX",
    },
    {
        "id": 2,
        "partner_name": "International Rice Research Institute",
        "acronym": "IRRI",
        "web_page": "https://www.irri.org",
        "institution_type": "Research Center",
        "country_id": "PH",
    },
    {
        "id": 3,
        "partner_name": "World Agroforestry Centre",
        "acronym": "ICRAF",
        "web_page": "https://www.worldagroforestry.org",
        "institution_type": "Research Center",
        "country_id": "KE",
    },
]


class ProcessingProgress:
    """Track processing progress."""

    def __init__(self, total: int):
        self.total = total
        self.processed = 0
        self.duplicates = 0
        self.potential_duplicates = 0
        self.errors = []

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "processed": self.processed,
            "total": self.total,
            "duplicates": self.duplicates,
            "potential_duplicates": self.potential_duplicates,
            "errors": self.errors,
        }


@router.post("/duplicates/upload")
async def upload_and_detect_duplicates(file: UploadFile = File(...)):
    """
    Upload an Excel file and detect duplicate institutions.
    
    Required columns: id, partner_name, institution_type, country_id
    Optional columns: acronym, web_page
    
    The endpoint will detect duplicates against CLARISA database institutions
    using semantic similarity and rule-based signals.

    Returns:
        JSON response with duplicate detection results
    """
    file_id = str(uuid.uuid4())

    try:
        # Read file
        file_content = await file.read()

        # Parse Excel file
        records, parse_errors = parse_excel_file(file_content)

        if parse_errors:
            raise HTTPException(
                status_code=400, detail={"error": "Excel parsing errors", "errors": parse_errors}
            )

        if not records:
            raise HTTPException(status_code=400, detail={"error": "No valid records found in Excel"})

        # Get services
        embeddings_service = get_embeddings_service()
        detector = get_duplicate_detector()
        supabase = get_supabase_client()
        audit_logger = get_audit_logger()

        # Get countries mapping for resolving country names
        countries_map = supabase.get_countries_map()

        # Log upload
        audit_logger.log_upload(file_id, file.filename, len(records))

        # Initialize progress tracker
        progress = ProcessingProgress(len(records))

        # Get CLARISA institutions (use mock if Supabase not available)
        try:
            clarisa_institutions = supabase.get_clarisa_institutions()
        except Exception as e:
            print(f"Could not fetch CLARISA institutions: {str(e)}, using mock data")
            clarisa_institutions = MOCK_CLARISA_INSTITUTIONS

        results = []

        # Process each uploaded record
        for record in records:
            row_id = str(record.get("id", "unknown"))
            progress.processed += 1

            try:
                # Build embedding text with exact format:
                # acronym: {acronym}, Partner_name: {institution_name}, institution_type: {institution_type}, website: {website}, country: {country_name}
                acronym = record.get("acronym", "")
                partner_name = record.get("partner_name", "")
                institution_type = record.get("institution_type", "")
                website = record.get("web_page", "")  # Note: API uses web_page
                country_id = record.get("country_id", "")
                country_name = countries_map.get(int(country_id)) if country_id else None
                
                parts = []
                if acronym:
                    parts.append(f"acronym: {acronym}")
                if partner_name:
                    parts.append(f"Partner_name: {partner_name}")
                if institution_type:
                    parts.append(f"institution_type: {institution_type}")
                if website:
                    parts.append(f"website: {website}")
                if country_name:
                    parts.append(f"country: {country_name}")
                
                embedding_text = ", ".join(parts)

                # Generate SINGLE embedding for uploaded institution (optimized for token cost)
                uploaded_embedding = embeddings_service.generate_embedding(embedding_text)

                # Find best match in CLARISA institutions
                best_match = None
                best_similarity = 0.0

                for clarisa_record in clarisa_institutions:
                    # Use pre-generated embedding from CLARISA database (no additional tokens)
                    clarisa_embedding = clarisa_record.get("embedding_vector")
                    
                    # ===== STRATEGY 1: ADVANCED MULTI-STRATEGY MATCHING (for 10K+ variants) =====
                    # This checks: exact, core name, fuzzy, acronym, keyword overlap
                    advanced_result = detector.advanced_multi_strategy_match(record, clarisa_record)
                    
                    # No need for debug logging - the results will speak for themselves
                    
                    if advanced_result["match_type"] != "no_match":
                        # Strong matches from advanced matching
                        signals = DetectionSignals()
                        
                        if advanced_result["match_type"] == "exact":
                            signals.exact_name_match = True
                        elif advanced_result["match_type"] == "acronym":
                            signals.acronym_similarity = advanced_result["confidence"]
                        elif advanced_result["match_type"] == "fuzzy":
                            signals.variant_name_match = True
                        elif advanced_result["match_type"] == "keyword":
                            signals.keyword_match_score = advanced_result["confidence"]
                        
                        best_match = {
                            "clarisa_id": clarisa_record.get("clarisa_id"),
                            "similarity": advanced_result["confidence"],
                            "signals": signals,
                            "explanation": advanced_result["explanation"],
                            "match_type": advanced_result["match_type"],
                        }
                        
                        # For exact and acronym matches, stop searching
                        if advanced_result["match_type"] in ["exact", "acronym"] and advanced_result["confidence"] >= 0.90:
                            break
                        
                        # For fuzzy and keyword, continue to see if we find better
                        if advanced_result["confidence"] > best_similarity:
                            best_similarity = advanced_result["confidence"]
                    
                    # ===== STRATEGY 2: SEMANTIC SIMILARITY (fallback if advanced matching didn't find strong match) =====
                    if (not best_match or best_match["similarity"] < 0.85):
                        if uploaded_embedding and clarisa_embedding:
                            combined_sim = embeddings_service.similarity_score(
                                uploaded_embedding,
                                clarisa_embedding
                            )
                        else:
                            combined_sim = 0.0

                        # Check for semantic candidate
                        rule_signals, is_candidate = detector.check_rule_based_signals(
                            record, clarisa_record, combined_sim
                        )
                        
                        # Track best semantic candidate
                        if is_candidate and combined_sim > best_similarity:
                            best_similarity = combined_sim
                            rule_signals.semantic_combined_similarity = combined_sim
                            best_match = {
                                "clarisa_id": clarisa_record.get("clarisa_id"),
                                "similarity": combined_sim,
                                "signals": rule_signals,
                                "match_type": "semantic",
                            }

                # Classify record
                if best_match and best_match["similarity"] > 0.0:
                    status, similarity, reason, matched_id = detector.classify_record(
                        record,
                        {
                            "similarity_score": best_match["similarity"],
                            "matched_clarisa_id": best_match["clarisa_id"],
                            "signals": best_match["signals"],
                            "match_type": best_match.get("match_type"),
                            "explanation": best_match.get("explanation"),
                        },
                    )
                else:
                    status, similarity, reason, matched_id = detector.classify_record(record)

                # Update progress
                if status == DuplicateStatus.DUPLICATE:
                    progress.duplicates += 1
                elif status == DuplicateStatus.POTENTIAL_DUPLICATE:
                    progress.potential_duplicates += 1

                # Log decision
                audit_logger.log_duplicate_detection(
                    file_id, row_id, record, matched_id, similarity, status.value, reason
                )

                # Add result
                # Build result with all fields needed by frontend
                results.append({
                    "id": row_id,
                    "institution_name": record.get("partner_name", ""),
                    "acronym": record.get("acronym", ""),
                    "status": status.value,
                    "similarity": round(similarity, 4),
                    "clarisa_match": matched_id,
                    "reason": reason,
                    "web_page": record.get("web_page", ""),
                    "type": record.get("institution_type", ""),
                    "country": record.get("country_id", ""),
                })

            except Exception as e:
                progress.errors.append(f"Row {row_id}: {str(e)}")
                audit_logger.log_error(file_id, row_id, str(e))

        # Prepare response
        response = {
            "file_id": file_id,
            "total_records": len(records),
            "results": results,
            "progress": progress.to_dict(),
        }

        # Save analysis records to database for future retrieval
        supabase.save_analysis_records(
            file_id=file_id,
            filename=file.filename or "unknown",
            total_records=len(records),
            results=results
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "CLARISA Partners Duplicate Detection Backend is running",
    }


@router.get("/config")
async def get_config():
    """Get current configuration (non-sensitive)."""
    return {
        "exact_match_threshold": settings.EXACT_MATCH_THRESHOLD,
        "potential_duplicate_threshold": settings.POTENTIAL_DUPLICATE_THRESHOLD,
        "duplicate_threshold": settings.DUPLICATE_THRESHOLD,
        "embedding_batch_size": settings.EMBEDDING_BATCH_SIZE,
    }


@router.post("/sync-countries")
async def sync_countries():
    """
    Sync countries from CLARISA API to Supabase.
    
    This endpoint:
    - Fetches all countries from CLARISA API
    - Uses CLARISA 'code' as the country ID (matching clarisa_institutions.country_id)
    - Inserts them into the countries table
    - Does NOT delete existing countries (use POST /delete-countries first if needed)
    
    Returns:
        JSON response with sync statistics
    """
    import logging
    logger = logging.getLogger(__name__)
    audit_logger = get_audit_logger()
    
    try:
        sync_service = get_clarisa_sync_service()
        
        logger.info("Starting CLARISA countries sync...")
        
        # Log the sync action
        audit_logger.log_audit_action(
            action="sync_countries_started",
            entity_type="country",
        )
        
        # Execute sync
        result = await sync_service.sync_countries()
        
        logger.info(f"Countries sync completed with result: {result}")
        
        # Log completion
        audit_logger.log_audit_action(
            action="sync_countries_completed",
            entity_type="country",
            details=result,
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.delete("/reset-all-data")
async def reset_all_data():
    """
    **DESTRUCTIVE OPERATION**: Reset all CLARISA data from scratch.
    
    This endpoint will:
    1. Delete all CLARISA institutions
    2. Delete all countries
    
    After this, you can run:
    - POST /sync-countries (to import countries from CLARISA)
    - POST /sync-clarisa (to import institutions from CLARISA)
    - POST /generate-embeddings (to generate embeddings)
    
    **WARNING**: This cannot be undone. All CLARISA data will be erased.
    
    Returns:
        JSON response with deletion statistics
    """
    import logging
    logger = logging.getLogger(__name__)
    audit_logger = get_audit_logger()
    
    try:
        sync_service = get_clarisa_sync_service()
        
        logger.info("Starting full data reset...")
        
        # Log the dangerous action
        audit_logger.log_audit_action(
            action="reset_all_data_started",
            entity_type="system",
        )
        
        # Execute reset
        result = await sync_service.reset_all_data()
        
        logger.info(f"Full data reset completed with result: {result}")
        
        # Log completion
        audit_logger.log_audit_action(
            action="reset_all_data_completed",
            entity_type="system",
            details=result,
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.delete("/delete-countries")
async def delete_all_countries():
    """
    Delete ALL countries from the database.
    
    **WARNING**: This will delete all countries. 
    After deleting, you must run POST /sync-countries to re-import from CLARISA.
    
    Returns:
        JSON response with deletion statistics
    """
    import logging
    logger = logging.getLogger(__name__)
    audit_logger = get_audit_logger()
    
    try:
        sync_service = get_clarisa_sync_service()
        
        logger.info("Starting countries deletion...")
        
        # Log the action
        audit_logger.log_audit_action(
            action="delete_countries_started",
            entity_type="country",
        )
        
        # Execute deletion
        result = await sync_service.delete_all_countries()
        
        logger.info(f"Countries deletion completed with result: {result}")
        
        # Log completion
        audit_logger.log_audit_action(
            action="delete_countries_completed",
            entity_type="country",
            details=result,
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.delete("/delete-clarisa-institutions")
async def delete_clarisa_institutions():
    """
    Delete ALL CLARISA institutions from the database.
    
    **WARNING**: This will delete all institutions.
    After deleting, you must run POST /sync-clarisa to re-import from CLARISA.
    
    Returns:
        JSON response with deletion statistics
    """
    import logging
    logger = logging.getLogger(__name__)
    audit_logger = get_audit_logger()
    
    try:
        sync_service = get_clarisa_sync_service()
        
        logger.info("Starting CLARISA institutions deletion...")
        
        # Log the action
        audit_logger.log_audit_action(
            action="delete_clarisa_institutions_started",
            entity_type="institution",
        )
        
        # Execute deletion
        result = await sync_service.delete_all_clarisa_institutions()
        
        logger.info(f"CLARISA institutions deletion completed with result: {result}")
        
        # Log completion
        audit_logger.log_audit_action(
            action="delete_clarisa_institutions_completed",
            entity_type="institution",
            details=result,
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.post("/sync-clarisa")
async def sync_clarisa_institutions():
    """
    Sync institutions from CLARISA API to Supabase database.
    
    This endpoint:
    - Fetches all institutions from CLARISA API
    - Saves institution types, countries, and institutions
    - Generates embeddings for each institution
    - Stores everything in Supabase
    
    Returns:
        JSON response with sync statistics
    """
    import logging
    logger = logging.getLogger(__name__)
    audit_logger = get_audit_logger()
    
    try:
        sync_service = get_clarisa_sync_service()
        
        logger.info("Starting CLARISA sync...")
        
        # Log the sync action
        audit_logger.log_audit_action(
            action="sync_clarisa_started",
            entity_type="institution",
        )
        
        # Execute sync
        result = await sync_service.sync_institutions()
        
        logger.info(f"Sync completed with result: {result}")
        
        # Log completion
        audit_logger.log_audit_action(
            action="sync_clarisa_completed",
            entity_type="institution",
            details=result,
        )
        
        return {
            "status": result.get("status"),
            "total_fetched": result.get("total_fetched"),
            "total_new": result.get("total_new"),
            "total_saved": result.get("total_saved"),
            "total_updated": result.get("total_updated"),
            "countries_synced": result.get("countries_synced"),
            "institution_types_synced": result.get("institution_types_synced"),
            "errors": result.get("errors", []),
            "debug_info": {
                "message": "Check backend logs if total_saved is 0 despite total_new > 0",
                "mock_mode": not settings.SUPABASE_KEY,
            }
        }
    except Exception as e:
        logger.error(f"Sync failed: {str(e)}", exc_info=True)
        
        audit_logger.log_audit_action(
            action="sync_clarisa_failed",
            entity_type="institution",
            details={"error": str(e)},
        )
        raise HTTPException(status_code=500, detail={"error": str(e), "type": type(e).__name__})


@router.get("/sync-status")
def get_sync_status():
    """
    Get the status of CLARISA sync.
    
    Returns:
        JSON response with sync statistics and instructions
    """
    try:
        supabase = get_supabase_client()
        
        # Get count of institutions
        institutions_count = supabase.get_institutions_count()
        countries_count = supabase.get_countries_count()
        embeddings_count = supabase.get_embeddings_count()
        
        response = {
            "institutions_count": institutions_count,
            "countries_count": countries_count,
            "embeddings_count": embeddings_count,
            "last_sync": "N/A",
        }
        
        # Add helpful message if no data
        if institutions_count == 0:
            response["message"] = "No institutions synced yet. Use POST /institutions/sync-clarisa to sync from CLARISA API"
            response["next_step"] = "POST /institutions/sync-clarisa"
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/test-clarisa-api")
async def test_clarisa_api():
    """
    Test connection to CLARISA API.
    
    Returns:
        Test results showing if CLARISA API is accessible
    """
    try:
        import httpx
        import logging
        logger = logging.getLogger(__name__)
        
        clarisa_url = settings.CLARISA_API_URL
        logger.info(f"Testing CLARISA API: {clarisa_url}")
        
        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            response = await client.get(
                clarisa_url,
                headers={"User-Agent": "CLARISA-AI-Partners/1.0"}
            )
            
            logger.info(f"Response status: {response.status_code}")
            
            data = response.json()
            
            # Determine structure
            if isinstance(data, dict):
                keys = list(data.keys())
                if "data" in data:
                    count = len(data["data"]) if isinstance(data["data"], list) else "unknown"
                    first_item = data["data"][0] if isinstance(data["data"], list) and data["data"] else None
                else:
                    count = len(data) if isinstance(data, list) else "unknown"
                    first_item = None
            elif isinstance(data, list):
                count = len(data)
                first_item = data[0] if data else None
                keys = []
            else:
                count = 0
                first_item = None
                keys = []
            
            return {
                "status": "success",
                "url": clarisa_url,
                "http_status": response.status_code,
                "response_type": str(type(data)),
                "response_keys": keys if isinstance(data, dict) else "N/A",
                "institution_count": count,
                "first_institution_sample": first_item,
            }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        
        raise HTTPException(status_code=500, detail={
            "error": str(e),
            "type": type(e).__name__,
            "clarisa_url": settings.CLARISA_API_URL
        })


@router.delete("/delete-embeddings")
async def delete_embeddings():
    """
    Delete ALL embeddings from the database.
    
    **WARNING**: This will delete all embeddings. 
    After deleting, you must run POST /generate-embeddings to regenerate them.
    
    Returns:
        JSON response with deletion statistics
    """
    import logging
    logger = logging.getLogger(__name__)
    audit_logger = get_audit_logger()
    
    try:
        sync_service = get_clarisa_sync_service()
        
        logger.info("Starting embeddings deletion...")
        
        # Log the action
        audit_logger.log_audit_action(
            action="delete_embeddings_started",
            entity_type="embedding",
        )
        
        # Execute deletion
        result = await sync_service.delete_all_embeddings()
        
        logger.info(f"Embeddings deletion completed with result: {result}")
        
        # Log completion
        audit_logger.log_audit_action(
            action="delete_embeddings_completed",
            entity_type="embedding",
            details=result,
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.post("/generate-embeddings")
async def generate_embeddings():
    """
    Generate embeddings for institutions without embeddings.
    
    This is a separate endpoint from sync-clarisa because:
    - Embeddings can fail without affecting the sync
    - Can be run asynchronously
    - Can be rate-limited independently
    
    Returns:
        JSON response with embedding generation status
    """
    try:
        from src.services.embedding_service import get_embedding_generation_service
        
        embedding_service = get_embedding_generation_service()
        result = embedding_service.generate_missing_embeddings()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/analysis")
async def get_analysis_list():
    """
    Get list of all analysis files uploaded.
    
    Returns:
        List of analyses with file_id, filename, and created_at timestamp
    """
    try:
        supabase = get_supabase_client()
        analyses = supabase.get_analysis_list()
        
        return {
            "total": len(analyses),
            "analyses": analyses,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/analysis/{file_id}")
async def get_analysis_details(file_id: str):
    """
    Get detailed results for a specific analysis.
    
    Args:
        file_id: The file ID from the upload
    
    Returns:
        Analysis details including summary and all records
    """
    try:
        supabase = get_supabase_client()
        details = supabase.get_analysis_details(file_id)
        
        if "error" in details:
            raise HTTPException(status_code=404, detail=details)
        
        return details
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.post("/debug/test-single-embedding")
async def test_single_embedding():
    """
    DEBUG: Generate embedding for a single institution and show exactly what's saved.
    
    This is for testing to ensure country_name is properly included in embeddings.
    """
    try:
        supabase = get_supabase_client()
        embedding_service = get_embeddings_service()
        
        # Get the embedding generation service which has _build_embedding_text
        from src.services.embedding_service import get_embedding_generation_service
        gen_service = get_embedding_generation_service()
        
        # Get ONE institution without embedding
        institutions = supabase.get_institutions_without_embeddings()
        
        if not institutions:
            return {
                "status": "no_institutions",
                "message": "All institutions already have embeddings or no institutions found"
            }
        
        inst = institutions[0]
        
        # Show what we're working with
        result = {
            "institution_id": inst.get("id"),
            "clarisa_id": inst.get("clarisa_id"),
            "institution_raw": inst,
            "country_id": inst.get("country_id"),
            "country_name": inst.get("country_name"),
            "embedding_text": "",
            "embedding_generated": False,
            "embedding_saved": False,
            "error": None,
        }
        
        # Build embedding text
        embedding_text = gen_service._build_embedding_text(inst)
        result["embedding_text"] = embedding_text
        
        if not embedding_text:
            result["error"] = "Empty embedding text - country field likely missing"
            return result
        
        # Check if country is in the text
        if "country:" in embedding_text:
            result["has_country_in_text"] = True
        else:
            result["has_country_in_text"] = False
            result["warning"] = "❌ Country field NOT found in embedding text!"
        
        # Generate embedding vector
        embedding_vector = embedding_service.generate_embedding(embedding_text)
        result["embedding_generated"] = bool(embedding_vector)
        
        if not embedding_vector:
            result["error"] = "Failed to generate embedding vector"
            return result
        
        # Save to database
        institution_id = inst.get("id")
        supabase.upsert_institution_embedding(
            institution_id=institution_id,
            embedding_text=embedding_text,
            embedding_vector=embedding_vector,
        )
        result["embedding_saved"] = True
        
        # Fetch it back to verify
        saved_result = supabase.client.table("institution_embeddings").select(
            "institution_id, embedding_text"
        ).eq("institution_id", institution_id).execute()
        
        if saved_result.data:
            saved_embedding = saved_result.data[0]
            result["saved_to_db"] = {
                "institution_id": saved_embedding.get("institution_id"),
                "embedding_text_in_db": saved_embedding.get("embedding_text"),
            }
            
            # Final verification
            if "country:" in saved_embedding.get("embedding_text", ""):
                result["status"] = "✅ SUCCESS - Country field IS in saved embedding"
            else:
                result["status"] = "❌ FAILED - Country field was NOT saved"
        
        return result
        
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@router.post("/admin/update-country-ids")
async def update_country_ids():
    """
    ADMIN: Update country_id in clarisa_institutions from CLARISA API.
    
    This fetches fresh data from CLARISA and updates the country_id field.
    """
    try:
        from src.services.clarisa_sync_service import get_clarisa_sync_service
        import logging
        
        logger = logging.getLogger(__name__)
        sync_service = get_clarisa_sync_service()
        supabase = get_supabase_client()
        
        # Fetch fresh data from CLARISA
        logger.info("Fetching fresh institution data from CLARISA...")
        institutions = await sync_service.fetch_clarisa_institutions()
        
        if not institutions:
            return {"status": "error", "message": "No institutions fetched from CLARISA"}
        
        # Check structure of first institution
        sample = institutions[0] if institutions else {}
        
        result = {
            "status": "completed",
            "total_fetched": len(institutions),
            "sample_institution_keys": list(sample.keys()),
            "sample_institution": sample,
            "updated": 0,
            "errors": [],
        }
        
        # Check if country_id exists in CLARISA records
        has_country_id = any(inst.get("country_id") for inst in institutions[:100])
        result["institutions_have_country_id"] = has_country_id
        
        if not has_country_id:
            # Check for alternative country field names
            sample_inst = institutions[0]
            potential_country_fields = [k for k in sample_inst.keys() if 'country' in k.lower()]
            result["potential_country_fields"] = potential_country_fields
            
            # Extract from countryOfficeDTO (headquarters)
            if "countryOfficeDTO" in sample_inst and sample_inst["countryOfficeDTO"]:
                logger.info("Found countryOfficeDTO in CLARISA. Extracting headquarters country...")
                
                for inst in institutions:
                    try:
                        clarisa_id = inst.get("code")
                        country_offices = inst.get("countryOfficeDTO", [])
                        
                        if clarisa_id and country_offices:
                            # Find headquarters country
                            hq_country = None
                            for office in country_offices:
                                if office.get("isHeadquarter") == 1:
                                    hq_country = office.get("code")
                                    break
                            
                            # Fallback to first country if no HQ found
                            if not hq_country and country_offices:
                                hq_country = country_offices[0].get("code")
                            
                            if hq_country:
                                supabase.client.table("clarisa_institutions").update({
                                    "country_id": hq_country
                                }).eq("clarisa_id", clarisa_id).execute()
                                
                                result["updated"] += 1
                    except Exception as e:
                        result["errors"].append(f"Error updating institution {inst.get('code')}: {str(e)}")
                
                result["message"] = f"Successfully extracted headquarters country from countryOfficeDTO"
            else:
                result["message"] = "CLARISA API does not appear to have country_id or countryOfficeDTO"
            
            return result
        
        # Update country_ids in database
        logger.info(f"Updating {len(institutions)} institutions with country IDs...")
        
        for inst in institutions:
            try:
                clarisa_id = inst.get("id")
                country_id = inst.get("country_id")
                
                if clarisa_id and country_id:
                    supabase.client.table("clarisa_institutions").update({
                        "country_id": country_id
                    }).eq("clarisa_id", clarisa_id).execute()
                    
                    result["updated"] += 1
            except Exception as e:
                result["errors"].append(f"Error updating institution {inst.get('id')}: {str(e)}")
        
        logger.info(f"Updated {result['updated']} institutions")
        return result
        
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }
