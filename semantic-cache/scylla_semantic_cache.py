from datetime import datetime
import uuid
import numpy as np
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from scylladb import ScyllaClient
from config import OPENAI_API

class ScyllaSemanticCacheApp:

    def __init__(self):
        self.scylla_client = ScyllaClient()
        self.openai_client = OpenAI(base_url=OPENAI_API["base_url"],
                                    api_key=OPENAI_API["apikey"])
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
    def ask_openai(self, prompt):
        completion = self.openai_client.chat.completions.create(
        model="openai/gpt-4.1-nano",
        messages=[{
            "role": "user",
            "content": prompt
            }],
        
        )
        return completion.choices[0].message.content
    
    def create_embedding(self, text):
        return self.embedding_model.encode(text).tolist()
    
    def calc_cosine_similarity(self, vec1, vec2):
        """Calculate cosine similarity between two vectors."""
        v1, v2 = np.array(vec1), np.array(vec2)
        return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    
    def search_cache(self, embedding, threshold=0.80):
        """       
        Returns the most similar response if it is above the threshold. Otherwise returns `None`.
        """
        k = 1
        cql = "SELECT * FROM prompts ORDER BY prompt_embedding ANN OF %s LIMIT %s;"
        results = self.scylla_client.query_data(cql, [embedding, k])
        if len(results) > 0:
            cached_response = results[0]
            similarity = self.calc_cosine_similarity(embedding, cached_response['prompt_embedding'])
            print("Similarity score:", similarity)
            if similarity >= threshold:
                return cached_response['llm_response']
        return None
    
    def insert_to_cache(self, prompt_text, prompt_embedding, llm_response):
        data = {"prompt_id": uuid.uuid4(),
                "prompt_text": prompt_text,
                "prompt_embedding": prompt_embedding,
                "llm_response": llm_response,
                "inserted_at": datetime.now()}
        self.scylla_client.insert_data("prompts", data)
        
    
    def semantic_cached_prompt(self, prompt):
        """Retrieve a response from ScyllaDB or ask OpenAI if it's a new prompt.

        Args:
            prompt (str): The user prompt.

        Returns:
            str: The response to the prompt.
        """
        embedding = self.create_embedding(prompt)
        
        cached_response = self.search_cache(embedding, threshold=0.80)
        if cached_response:
            print("Cache hit! Returning cached response...")
            return cached_response
        else:
            print("Cache miss... sending request to OpenAI!")
            response = self.ask_openai(prompt)
            self.insert_to_cache(prompt, embedding, response)
            return response
        
if __name__ == "__main__":
    app = ScyllaSemanticCacheApp()
    
    # response comes from LLM
    question = "What is the capital city of France?"
    print("Question 1:", question)
    answer = app.semantic_cached_prompt(question)
    print("Answer:", answer)
    
    # response comes from cache
    question = "What's the capital of France?"
    print("\nQuestion 2:", question)
    answer = app.semantic_cached_prompt(question)
    print("Answer:", answer)