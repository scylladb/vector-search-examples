CREATE KEYSPACE rag WITH replication = {'class': 'NetworkTopologyStrategy', 'replication_factor': '3'}
AND TABLETS = {'enabled': 'false'};

CREATE TABLE rag.chunks (
    chunk_id UUID PRIMARY KEY,
    text TEXT,
    embedding vector<float, 768>
) WITH cdc = {'enabled': 'true'};


CREATE INDEX IF NOT EXISTS ann_index ON rag.chunks(embedding)
USING 'vector_index'
WITH OPTIONS = { 'similarity_function': 'DOT_PRODUCT' };