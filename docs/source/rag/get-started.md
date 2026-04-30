# Get started with RAG

This tutorial shows you how to run a Retrieval-Augmented Generation (RAG) chatbot powered by [ScyllaDB Vector Search](https://www.scylladb.com/product/vector-search/) and [Groq](https://console.groq.com/).

## What you'll build
A movie chatbot that retrieves semantically relevant movie plots from ScyllaDB using vector similarity search and uses an LLM to generate responses grounded in that context. The retrieval step uses ScyllaDB's **local vector indexes** to scope ANN queries to a specific genre partition, returning only relevant context to the LLM.

## How filtered retrieval works

Without filtering, an ANN query scans all stored embeddings and returns the most similar results regardless of metadata. For RAG, this means the LLM may receive irrelevant context. For example, a query about 1980s horror movies could surface results from unrelated genres or eras.

ScyllaDB solves this with **local vector indexes**: a per-partition HNSW index that restricts the search space to rows matching a partition key before running ANN. The result is fast, scoped retrieval that gives the LLM only the context it needs.

| | Global index | Local index |
|---|---|---|
| **Scope** | All rows in the table | Rows within one partition |
| **WHERE clause** | Requires `ALLOW FILTERING` | Uses the partition key — no `ALLOW FILTERING` |
| **Performance** | Slower — scans the entire index | Fast — searches only the target partition's HNSW index |
| **RAG use case** | Full-corpus search | Per-genre, per-user, or per-category scoped retrieval |

## Prerequisites
* You've read the [Quick Start Guide to Vector Search](https://cloud.docs.scylladb.com/stable/vector-search/vector-search-quick-start.html)
* [ScyllaDB Cloud](https://cloud.scylladb.com/) cluster with `vector search` enabled
* [Python 3.11 or newer](https://www.python.org/downloads/) installed
* [Groq API key](https://console.groq.com/) (free tier is sufficient)
* [Git](https://git-scm.com/downloads) installed

## Clone the repository
Clone the repository and navigate to the project folder:

```bash
git clone https://github.com/scylladb/vector-search-examples.git
cd vector-search-examples/rag-movie-chatbot
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
* **streamlit** — interactive web UI

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
SCYLLADB_KEYSPACE=recommend
GROQ_API_KEY=your-groq-api-key
```

Find your ScyllaDB Cloud credentials in the [ScyllaDB Cloud console](https://cloud.scylladb.com/) under your cluster's **Connect** tab.

## Set up the database

### Create the schema
Run the migration script to create the keyspace, table, and vector index:

```bash
python db/migrate.py
```

You should see:
```
Creating keyspace and tables...
Migration completed.
```

### Load sample data
With the schema in place, load the sample movie dataset. The data is shared with the movie recommendation example — run its loader from the repository root:

```bash
cd ../movie-recommendation
cp ../rag-movie-chatbot/.env .env
docker build -t movies-app .
docker run -d --rm -p 8000:8000 --network host --env-file .env --name movie-container movies-app
docker exec movie-container python src/load_data.py
```

This ingests approximately 30,000 movies from the [TMDB dataset](https://www.kaggle.com/datasets/asaniczka/tmdb-movies-dataset-2023-930k-movies/), generating 384-dimensional embeddings for each plot using the `all-MiniLM-L6-v2` model.

Once the data is loaded, stop the container and return to the chatbot folder:

```bash
docker stop movie-container
cd ../rag-movie-chatbot
```

## Run the application

Start the Streamlit app:

```bash
uv run streamlit run app.py
```

Then open your browser to **[http://localhost:8501](http://localhost:8501)**.

You can now enter movie plots or descriptions, and the chatbot will:
1. Convert your input to a vector embedding
2. Run an ANN query against ScyllaDB to retrieve semantically similar movie plots
3. Pass the retrieved plots as context to the Groq LLM
4. Stream back a response grounded in actual movies from the database

Check the source code of the application for more details:
https://github.com/scylladb/vector-search-examples/tree/main/rag-movie-chatbot

## Understanding the database schema

The migration script creates the following schema in your ScyllaDB cluster:

```cql
CREATE KEYSPACE recommend 
WITH replication = {'class': 'NetworkTopologyStrategy', 'replication_factor': '3'};

CREATE TABLE recommend.movies (
    id           INT,
    release_date TIMESTAMP,
    title        TEXT,
    tagline      TEXT,
    genre        TEXT,
    imdb_id      TEXT,
    poster_url   TEXT,
    plot         TEXT,
    plot_embedding VECTOR<FLOAT, 384>,
    PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ann_index 
  ON recommend.movies(plot_embedding) 
  USING 'vector_index'
  WITH OPTIONS = { 'similarity_function': 'DOT_PRODUCT' };
```

**Keyspace:**
- `NetworkTopologyStrategy` with `replication_factor: 3` replicates data across three nodes for high availability.

**Table:**
- `plot_embedding VECTOR<FLOAT, 384>` stores a 384-dimensional float vector for each movie plot, generated using [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) from Sentence Transformers.
- `PRIMARY KEY (id)` distributes rows evenly across the cluster.

**Vector index:**
```cql
CREATE INDEX IF NOT EXISTS ann_index 
  ON recommend.movies(plot_embedding) 
  USING 'vector_index'
  WITH OPTIONS = { 'similarity_function': 'DOT_PRODUCT' };
```

This creates an Approximate Nearest Neighbor (ANN) index on the `plot_embedding` column using HNSW, enabling fast similarity queries. `DOT_PRODUCT` is used because `all-MiniLM-L6-v2` produces normalized (unit-length) vectors — for normalized vectors, dot product is equivalent to cosine similarity but computationally faster.

The retrieval query looks like this:

```cql
SELECT * FROM recommend.movies
ORDER BY plot_embedding ANN OF [0.12, -0.34, ...]
LIMIT 5;
```

For filtered retrieval scoped to a single genre, the schema uses a second table with `genre` as the partition key and a local vector index:

```cql
CREATE TABLE recommend.movies_by_genre (
    genre        TEXT,
    id           INT,
    release_date TIMESTAMP,
    title        TEXT,
    plot         TEXT,
    plot_embedding VECTOR<FLOAT, 384>,
    PRIMARY KEY (genre, id)
);

CREATE CUSTOM INDEX IF NOT EXISTS ann_index_by_genre
  ON recommend.movies_by_genre((genre), plot_embedding)
  USING 'vector_index'
  WITH OPTIONS = { 'similarity_function': 'DOT_PRODUCT' };
```

The local index syntax `((genre), plot_embedding)` tells ScyllaDB to build a separate HNSW index per genre value. Queries on this table specify the partition key and need no `ALLOW FILTERING`:

```cql
SELECT * FROM recommend.movies_by_genre
WHERE genre = 'Science Fiction'
ORDER BY plot_embedding ANN OF [0.12, -0.34, ...]
LIMIT 5;
```

ScyllaDB routes the query to the correct shard and searches only that partition's index — keeping retrieval fast as the dataset grows.

## Next steps

The [RAG tutorial](rag-chatbot-scylladb.md) walks through building the full filtering pipeline step by step: schema design, embedding-based retrieval, genre and decade filters, the RAG module, and the Groq integration.
