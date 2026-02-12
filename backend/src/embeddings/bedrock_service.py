"""Embeddings service using AWS Bedrock Titan v2."""

import boto3
import json
import hashlib
from typing import List, Optional
from src.config import settings


class EmbeddingsService:
    """Service for generating embeddings using AWS Bedrock Titan v2."""

    def __init__(self):
        """Initialize Bedrock client."""
        self.use_mock = settings.USE_MOCK_EMBEDDINGS
        if not self.use_mock:
            self.bedrock_client = boto3.client(
                "bedrock-runtime",
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
        self.model_id = "amazon.titan-embed-text-v2:0"

    def _generate_mock_embedding(self, text: str) -> List[float]:
        """Generate a deterministic mock embedding."""
        hash_obj = hashlib.sha256(text.lower().encode())
        hash_hex = hash_obj.hexdigest()
        # Create a 1024-dimensional embedding from the hash
        embedding = []
        for i in range(0, 1024, 8):
            val = int(hash_hex[i % len(hash_hex) : (i % len(hash_hex)) + 8], 16)
            embedding.append((val % 2000 - 1000) / 1000.0)
        return embedding

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text."""
        if not text or not text.strip():
            return None

        try:
            if self.use_mock:
                return self._generate_mock_embedding(text)

            request_body = json.dumps({"inputText": text})

            response = self.bedrock_client.invoke_model(
                modelId=self.model_id, body=request_body, contentType="application/json"
            )

            response_body = json.loads(response.get("body").read())
            embedding = response_body.get("embedding", [])

            return embedding if embedding else None

        except Exception as e:
            print(f"Error generating embedding: {str(e)}")
            return self._generate_mock_embedding(text)

    def similarity_score(
        self, embedding1: List[float], embedding2: List[float]
    ) -> float:
        """Calculate cosine similarity between two embeddings."""
        if not embedding1 or not embedding2:
            return 0.0

        if len(embedding1) != len(embedding2):
            return 0.0

        # Cosine similarity
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        magnitude1 = sum(a * a for a in embedding1) ** 0.5
        magnitude2 = sum(b * b for b in embedding2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)


# Global instance
_embeddings_service: Optional[EmbeddingsService] = None


def get_embeddings_service() -> EmbeddingsService:
    """Get or create embeddings service instance."""
    global _embeddings_service
    if _embeddings_service is None:
        _embeddings_service = EmbeddingsService()
    return _embeddings_service
