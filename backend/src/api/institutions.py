"""Main API router for institutions duplicate detection."""

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Optional
import uuid
import json

from src.services.excel_parser import parse_excel_file, ExcelParsingError
from src.services.normalization import build_embedding_text, normalize_text
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
                # acronym: {acronym}, Partner_name: {institution_name}, institution_type: {Institution_type_id}, website: {website}, country: {country_id}
                acronym = record.get("acronym", "")
                partner_name = record.get("partner_name", "")
                institution_type = record.get("institution_type", "")
                website = record.get("web_page", "")  # Note: API uses web_page, DB might have website
                country_id = record.get("country_id", "")
                
                parts = []
                if acronym:
                    parts.append(f"acronym: {acronym}")
                if partner_name:
                    parts.append(f"Partner_name: {partner_name}")
                if institution_type:
                    parts.append(f"institution_type: {institution_type}")
                if website:
                    parts.append(f"website: {website}")
                if country_id:
                    parts.append(f"country: {country_id}")
                
                embedding_text = ", ".join(parts)

                # Generate SINGLE embedding for uploaded institution (optimized for token cost)
                uploaded_embedding = embeddings_service.generate_embedding(embedding_text)

                # Find best match in CLARISA institutions
                best_match = None
                best_similarity = 0.0

                for clarisa_record in clarisa_institutions:
                    # Use pre-generated embedding from CLARISA database (no additional tokens)
                    clarisa_embedding = clarisa_record.get("embedding_vector")
                    
                    # ===== RULE 1: Check for EXACT NAME MATCH (HIGHEST PRIORITY) =====
                    # Compare ONLY institution names, ignore country/type/website
                    if detector.check_exact_name_match(record, clarisa_record):
                        # Exact name match = DUPLICATE
                        signals = DetectionSignals()
                        signals.exact_name_match = True
                        best_match = {
                            "clarisa_id": clarisa_record.get("clarisa_id"),  # Use external clarisa_id
                            "similarity": 1.0,
                            "signals": signals,
                        }
                        break  # Stop searching, this is the best possible match

                    # ===== RULE 3: If no exact match, use SEMANTIC SIMILARITY on NAME ONLY =====
                    if uploaded_embedding and clarisa_embedding:
                        # Compare embeddings (which are based on FULL info but we use for name matching)
                        combined_sim = embeddings_service.similarity_score(
                            uploaded_embedding,
                            clarisa_embedding
                        )
                    else:
                        combined_sim = 0.0

                    # ===== RULE 4-6: Check for possible semantic match =====
                    rule_signals, is_candidate = detector.check_rule_based_signals(
                        record, clarisa_record, combined_sim
                    )

                    # Track best candidate (Rule 4: these will be POSSIBLE_DUPLICATE, not DUPLICATE)
                    if is_candidate and combined_sim > best_similarity:
                        best_similarity = combined_sim
                        rule_signals.semantic_combined_similarity = combined_sim
                        best_match = {
                            "clarisa_id": clarisa_record.get("clarisa_id"),  # Use external clarisa_id
                            "similarity": combined_sim,
                            "signals": rule_signals,
                        }

                # Classify record
                if best_match and best_match["similarity"] > 0.0:
                    status, similarity, reason, matched_id = detector.classify_record(
                        record,
                        {
                            "similarity_score": best_match["similarity"],
                            "matched_clarisa_id": best_match["clarisa_id"],
                            "signals": best_match["signals"],
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
        result = await embedding_service.generate_missing_embeddings()
        
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
