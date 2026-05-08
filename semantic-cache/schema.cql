CREATE KEYSPACE IF NOT EXISTS semantic_cache WITH replication = {'class': 'NetworkTopologyStrategy', 'replication_factor': '3'};

CREATE TABLE IF NOT EXISTS semantic_cache.prompts (
    prompt_id uuid PRIMARY KEY,
    inserted_at timestamp,
    prompt_text text,
    prompt_embedding vector<float, 384>,
    llm_response text
);

CREATE INDEX IF NOT EXISTS ann_index ON semantic_cache.prompts(prompt_embedding) 
USING 'vector_index'
WITH OPTIONS = { 'similarity_function': 'DOT_PRODUCT' };
