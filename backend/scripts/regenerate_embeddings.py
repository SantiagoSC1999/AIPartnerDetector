"""Regenerate all embeddings in batches."""

import asyncio
import logging
from src.persistence.supabase_client import get_supabase_client
from src.embeddings.bedrock_service import get_embeddings_service
from src.services.normalization import build_embedding_text

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def regenerate_embeddings_batch():
    """Regenerate all embeddings in batches."""
    supabase = get_supabase_client()
    embeddings_service = get_embeddings_service()
    
    BATCH_SIZE = 100
    
    try:
        # Get all institutions
        logger.info("Fetching all institutions...")
        institutions_response = supabase.client.table("clarisa_institutions").select(
            "id, name, acronym, institution_type, website, country_id"
        ).range(0, 20000).execute()
        
        institutions = institutions_response.data or []
        total = len(institutions)
        logger.info(f"Found {total} institutions to process")
        
        # Process in batches
        for batch_start in range(0, total, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total)
            batch = institutions[batch_start:batch_end]
            
            logger.info(f"Processing batch {batch_start//BATCH_SIZE + 1}: {batch_start+1} to {batch_end}/{total}")
            
            batch_embeddings = []
            
            for inst in batch:
                try:
                    inst_id = inst.get("id")
                    
                    # Build embedding text with exact format:
                    # acronym: {acronym}, Partner_name: {institution_name}, institution_type: {Institution_type_id}, website: {website}, country: {country_id}
                    acronym = inst.get("acronym", "")
                    partner_name = inst.get("name", "")
                    institution_type = inst.get("institution_type", "")
                    website = inst.get("website", "")
                    country_id = inst.get("country_id", "")
                    
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
                    
                    # Generate embedding
                    embedding_vector = await embeddings_service.generate_embedding(embedding_text)
                    
                    if embedding_vector:
                        batch_embeddings.append({
                            "institution_id": inst_id,
                            "embedding_text": embedding_text,
                            "embedding_vector": embedding_vector,
                        })
                        logger.debug(f"Generated embedding for institution {inst_id}: {partner_name}")
                        logger.debug(f"  Text: {embedding_text}")
                    else:
                        logger.warning(f"Failed to generate embedding for institution {inst_id}")
                        
                except Exception as e:
                    logger.error(f"Error processing institution {inst.get('id')}: {str(e)}")
                    continue
            
            # Save batch to database
            if batch_embeddings:
                try:
                    logger.info(f"Saving {len(batch_embeddings)} embeddings to database...")
                    result = supabase.client.table("institution_embeddings").upsert(
                        batch_embeddings,
                        on_conflict="institution_id"
                    ).execute()
                    logger.info(f"Batch {batch_start//BATCH_SIZE + 1} saved successfully")
                except Exception as e:
                    logger.error(f"Error saving batch: {str(e)}")
            
            # Small delay between batches to avoid rate limiting
            await asyncio.sleep(1)
        
        # Verify
        final_count = supabase.client.table("institution_embeddings").select(
            "count", count="exact"
        ).execute()
        logger.info(f"✓ Embedding regeneration complete! Total embeddings: {final_count.count}")
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(regenerate_embeddings_batch())
