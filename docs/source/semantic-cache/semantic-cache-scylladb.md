# Get started with semantic cache

This tutorial shows you how to run a **semantic cache layer** using [Groq](https://console.groq.com/) and ScyllaDB.

Semantic caching allows you to reuse previous responses by matching new queries to semantically similar ones, reducing redundant LLM API calls, lowering costs, and improving response times.

Source code is [available on GitHub](https://github.com/scylladb/vector-search-examples/tree/main/semantic-cache).

## Prerequisites
* [ScyllaDB Cloud account](https://cloud.scylladb.com/) with vector search enabled
* [Groq API key](https://console.groq.com/) (free tier is sufficient)
* [Python 3.11 or newer](https://www.python.org/downloads/)
* [uv](https://docs.astral.sh/uv/getting-started/installation/) package manager
* [Git](https://git-scm.com/downloads) installed

## Clone the repository
Clone the repository and navigate to the project folder:

```bash
git clone https://github.com/scylladb/vector-search-examples.git
cd vector-search-examples/semantic-cache
```

## Install dependencies

Install and sync dependencies with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

This creates a virtual environment and installs:
* **scylla-driver** — connects to ScyllaDB with DC-aware load balancing
* **sentence-transformers** — generates 384-dimensional embeddings from text
* **groq** — fast LLM inference for the generation step

If you don't have `uv` installed, follow the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/).

## Configure credentials
Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Open `.env` and fill in your ScyllaDB Cloud connection details and Groq API key:

```bash
SCYLLADB_HOST=node-0.aws-us-east-1.xxxxxxxx.clusters.scylla.cloud
SCYLLADB_PORT=9042
SCYLLADB_USERNAME=scylla
SCYLLADB_PASSWORD=your-password
SCYLLADB_DATACENTER=AWS_US_EAST_1
SCYLLADB_KEYSPACE=semantic_cache

GROQ_API_KEY=your-groq-api-key
```

Find your ScyllaDB Cloud credentials in the [ScyllaDB Cloud console](https://cloud.scylladb.com/) under your cluster's **Connect** tab.

## Set up the database

Run the migration script to create the keyspace, table, and vector index:

```bash
uv run python migrate.py
```

You should see:
```
Creating keyspace and tables...
Migration completed.
```

## Run the application

```bash
uv run python scylla_semantic_cache.py
```

The first run queries the LLM. A semantically similar follow-up question is served directly from the cache:

```
Q: What is the capital city of France?
Cache miss. Querying LLM...
...answer...

Q: What's the capital of France?
  Nearest cache similarity: 0.9823
Cache hit! Returning cached response.
...answer...
```

## Understanding the code

### Database schema

The migration script creates the following schema in your ScyllaDB cluster:

```cql
CREATE KEYSPACE IF NOT EXISTS semantic_cache
  WITH replication = {'class': 'NetworkTopologyStrategy', 'replication_factor': '3'};

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
```

`prompt_embedding VECTOR<FLOAT, 384>` stores a 384-dimensional embedding of each prompt, generated using [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) from Sentence Transformers. The `DOT_PRODUCT` similarity function works efficiently with the normalized (unit-length) vectors this model produces.

### App class

`ScyllaSemanticCacheApp` wires together the ScyllaDB client, the Groq LLM, and the embedding model:

```py
class ScyllaSemanticCacheApp:
    def __init__(self):
        self.scylla_client = ScyllaClient()
        self.groq_client = Groq(api_key=GROQ_API_KEY)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
```

### Similarity search with ScyllaDB

`search_cache()` uses ScyllaDB's ANN search together with the built-in `similarity_dot_product()` function to score the nearest match directly in the database — no need to fetch embeddings back or compute similarity in Python:

```py
def search_cache(self, embedding, threshold=0.90):
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
```

### Full caching flow

`semantic_cached_prompt()` ties everything together:

```py
def semantic_cached_prompt(self, prompt):
    embedding = self.create_embedding(prompt)
    cached_response = self.search_cache(embedding)
    if cached_response:
        print("Cache hit! Returning cached response.")
        return cached_response
    print("Cache miss. Querying LLM...")
    response = self.ask_llm(prompt)
    self.insert_to_cache(prompt, embedding, response)
    return response
```

1. Convert the prompt to a vector embedding.
2. Query ScyllaDB for the nearest cached embedding using ANN.
3. If the similarity score meets the threshold (0.90), return the cached response — **cache hit**.
4. Otherwise, call the Groq LLM, store the new response in ScyllaDB, and return it — **cache miss**.

## Relevant resources
* [ScyllaDB Cloud](https://cloud.scylladb.com/)
* [ScyllaDB Documentation](https://docs.scylladb.com/)
* [Groq API](https://console.groq.com/)

