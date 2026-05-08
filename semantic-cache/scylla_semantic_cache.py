from datetime import datetime
import time
import uuid
from groq import Groq
from sentence_transformers import SentenceTransformer
from scylladb import ScyllaClient
from config import GROQ_API_KEY, GROQ_MODEL

class ScyllaSemanticCacheApp:

    def __init__(self):
        self.scylla_client = ScyllaClient()
        self.groq_client = Groq(api_key=GROQ_API_KEY)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
    def ask_llm(self, prompt):
        completion = self.groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{
                "role": "user",
                "content": prompt
            }],
        )
        return completion.choices[0].message.content
    
    def create_embedding(self, text):
        return self.embedding_model.encode(text).tolist()
    
    def search_cache(self, embedding, threshold=0.90):
        """Return a cached response if a semantically similar prompt exists above the threshold."""
        k = 1
        cql = """SELECT llm_response, similarity_dot_product(prompt_embedding, %s) AS similarity
                 FROM prompts ORDER BY prompt_embedding ANN OF %s LIMIT %s;"""
        results = self.scylla_client.query_data(cql, [embedding, embedding, k])
        if results:
            cached = results[0]
            similarity = cached['similarity']
            print(f"  Nearest cache similarity: {similarity:.4f}")
            if similarity >= threshold:
                return cached['llm_response']
        return None
    
    def insert_to_cache(self, prompt_text, prompt_embedding, llm_response):
        data = {
            "prompt_id": uuid.uuid4(),
            "prompt_text": prompt_text,
            "prompt_embedding": prompt_embedding,
            "llm_response": llm_response,
            "inserted_at": datetime.now(),
        }
        self.scylla_client.insert_data("prompts", data)
    
    def semantic_cached_prompt(self, prompt):
        """Look up the cache; call the LLM only on a cache miss."""
        embedding = self.create_embedding(prompt)
        cached_response = self.search_cache(embedding)
        if cached_response:
            print("Cache hit! Returning cached response.")
            return cached_response
        print("Cache miss. Querying LLM...")
        response = self.ask_llm(prompt)
        self.insert_to_cache(prompt, embedding, response)
        time.sleep(1)  # allow the ANN index to ingest the insert
        return response
        
if __name__ == "__main__":
    app = ScyllaSemanticCacheApp()
    
    # First query — goes to the LLM
    question = "What is the capital city of France?"
    print(f"Q: {question}")
    print(app.semantic_cached_prompt(question))
    
    # Semantically similar — served from cache
    question = "What's the capital of France?"
    print(f"\nQ: {question}")
    print(app.semantic_cached_prompt(question))