"""Configuration settings for the CLARISA AI Partners backend."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    # Supabase
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
    USE_MOCK_SUPABASE = os.getenv("USE_MOCK_SUPABASE", "false").lower() == "true"
    
    # AWS
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    
    # Embeddings
    USE_MOCK_EMBEDDINGS = os.getenv("USE_MOCK_EMBEDDINGS", "false").lower() == "true"
    EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "10"))
    
    # CLARISA API
    CLARISA_API_URL = os.getenv("CLARISA_API_URL", "https://api.clarisa.cgiar.org/api/institutions")
    CLARISA_COUNTRIES_API_URL = os.getenv("CLARISA_COUNTRIES_API_URL", "https://api.clarisa.cgiar.org/api/countries")
    
    # Thresholds for duplicate detection
    EXACT_MATCH_THRESHOLD = float(os.getenv("EXACT_MATCH_THRESHOLD", "1.0"))
    POTENTIAL_DUPLICATE_THRESHOLD = float(os.getenv("POTENTIAL_DUPLICATE_THRESHOLD", "0.75"))
    DUPLICATE_THRESHOLD = float(os.getenv("DUPLICATE_THRESHOLD", "0.75"))


settings = Settings()
