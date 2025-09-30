from sentence_transformers import SentenceTransformer

class EmbeddingCreator:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.embedding_model = SentenceTransformer(model_name, device='cpu')
    
    def create_embedding(self, text: str) -> list[float]:
        """
        Get embedding for a single text input using SentenceTransformer.
        Returns the embedding vector.
        """
        return self.embedding_model.encode(text).tolist()