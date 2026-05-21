-- mem0 ScyllaDB schema
-- Embedding model: sentence-transformers/all-MiniLM-L6-v2 (384 dims)
--
--

-- Keyspace
-- NetworkTopologyStrategy is required — tablets (needed for vector columns)
-- are not supported with SimpleStrategy.
CREATE KEYSPACE IF NOT EXISTS mem0
  WITH replication = {'class': 'NetworkTopologyStrategy', 'replication_factor': 3};

-- Memories table
-- mem0 creates this automatically, but this script documents the exact schema.
CREATE TABLE IF NOT EXISTS mem0.memories (
    id         UUID,
    user_id    TEXT,
    agent_id   TEXT,
    run_id     TEXT,
    hash       TEXT,
    data       TEXT,
    metadata   TEXT,
    vector     vector<float, 384>,  -- all-MiniLM-L6-v2 output dimension
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (id)
);

-- Vector (HNSW) index for ANN similarity search
CREATE CUSTOM INDEX IF NOT EXISTS memories_vector_idx
    ON mem0.memories (vector)
    USING 'vector_index'
    WITH OPTIONS = {'similarity_function': 'COSINE'};

-- Secondary index on user_id for per-user memory lookups
CREATE INDEX IF NOT EXISTS memories_user_id_idx
    ON mem0.memories (user_id);
