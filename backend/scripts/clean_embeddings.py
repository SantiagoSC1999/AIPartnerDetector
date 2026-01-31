"""Clean embeddings in small chunks to avoid timeout."""

from src.persistence.supabase_client import get_supabase_client
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

supabase = get_supabase_client()

try:
    logger.info("Attempting to delete embeddings in chunks...")
    
    # Delete in chunks of 500
    chunk_size = 500
    deleted = 0
    
    while True:
        logger.info(f"Getting next {chunk_size} records to delete...")
        
        # Get IDs of next chunk
        result = supabase.client.table("institution_embeddings").select("id").limit(chunk_size).execute()
        
        if not result.data:
            logger.info("No more records to delete")
            break
        
        ids = [r["id"] for r in result.data]
        logger.info(f"Found {len(ids)} records, deleting...")
        
        # Delete by IDs
        delete_result = supabase.client.table("institution_embeddings").delete().in_("id", ids).execute()
        deleted += len(ids)
        logger.info(f"Deleted {len(ids)} records, total: {deleted}")
        
        time.sleep(0.5)  # Small delay between chunks
    
    # Verify
    count_after = supabase.client.table("institution_embeddings").select("count", count="exact").execute()
    logger.info(f"Final count: {count_after.count}")
    
    if count_after.count == 0:
        logger.info("✓ All embeddings deleted successfully!")
    else:
        logger.warning(f"⚠ Still {count_after.count} embeddings remaining")
    
except Exception as e:
    logger.error(f"Error: {str(e)}", exc_info=True)
