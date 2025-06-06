from typing import List
import numpy as np
from ...core.config import get_settings

settings = get_settings()

class EmbeddingGenerator:
    """Generate embeddings for text using various models"""
    
    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the embedding model based on configuration"""
        if self.model_name == "text-embedding-ada-002":
            self._init_openai()
        elif self.model_name in ["all-mpnet-base-v2", "all-MiniLM-L6-v2"]:
            self._init_sentence_transformers()
        else:
            raise ValueError(f"Unsupported embedding model: {self.model_name}")
    
    def _init_openai(self):
        """Initialize OpenAI embedding model"""
        from openai import OpenAI

        cleaned_key = settings.OPENAI_API_KEY.strip()
        print(f"[DEBUG] Cleaned API KEY for client: {repr(cleaned_key)}")

        # Crée un client OpenAI avec la clé propre
        self.client = OpenAI(api_key=cleaned_key)
    
    def _init_sentence_transformers(self):
        """Initialize Sentence Transformers embedding model"""
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(self.model_name)
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        if not texts:
            return []
        
        if self.model_name == "text-embedding-ada-002":
            return self._generate_openai_embeddings(texts)
        else:
            return self._generate_st_embeddings(texts)
    
    def _generate_openai_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI's API"""
        # Split into batches of 1000 (OpenAI's limit)
        batch_size = 1000
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            response = self.client.embeddings.create(
                model=self.model_name,
                input=batch_texts
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
    
    def _generate_st_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Sentence Transformers"""
        embeddings = self.model.encode(texts)
        return embeddings.tolist()  # Convert numpy arrays to lists for JSON serialization
