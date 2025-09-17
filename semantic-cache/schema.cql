CREATE KEYSPACE semantic_cache WITH replication = {'class': 'NetworkTopologyStrategy', 'replication_factor': '3'}
AND TABLETS = {'enabled': 'false'};

CREATE TABLE semantic_cache.prompts (
    prompt_id uuid PRIMARY KEY,
    inserted_at timestamp,
    prompt_text text,
    prompt_embedding vector<float, 384>,
    llm_response text,
    updated_at timestamp
) WITH cdc = {'enabled': 'true'};

CREATE INDEX IF NOT EXISTS ann_index ON semantic_cache.prompts(prompt_embedding) 
USING 'vector_index'
WITH OPTIONS = { 'similarity_function': 'DOT_PRODUCT' };