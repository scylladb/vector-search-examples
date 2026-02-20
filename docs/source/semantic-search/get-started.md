# Get started with semantic search

This tutorial shows you how to build a semantic search application with [ScyllaDB Vector Search](https://www.scylladb.com/product/vector-search/).

## What you'll build
A movie recommendation chatbot that uses ScyllaDB Vector Search to perform semantic similarity search between user queries and movie plot descriptions.

## Prerequisites
* You've read [Quick Start Guide to Vector Search](https://cloud.docs.scylladb.com/stable/vector-search/vector-search-quick-start.html) 
* [ScyllaDB Cloud](https://cloud.scylladb.com/) cluster with `vector search` enabled
* [Docker](https://docs.docker.com/get-docker/) installed
* [Git](https://git-scm.com/downloads) installed

## Clone the repository
Clone the repository and navigate to the project folder:

```bash
git clone https://github.com/scylladb/vector-search-examples.git
cd vector-search-examples/movie-recommendation
```

## Configure database credentials
Create a `.env` file from the example template:

```bash
cp .env.example .env
```

Edit `.env` and add your ScyllaDB Cloud credentials:
```
SCYLLADB_HOST=node-0.aws-us-east-1.xxxxxxxx.clusters.scylla.cloud
SCYLLADB_PORT=9042
SCYLLADB_USERNAME=scylla
SCYLLADB_PASSWORD=xxxxxxxxxxxxxx
SCYLLADB_DATACENTER=AWS_US_EAST_1
SCYLLADB_KEYSPACE=recommend
```

The `SCYLLADB_KEYSPACE` variable sets the keyspace name that will be created in your cluster.

## Run the application

### Build the Docker image
Build the Docker image from the project directory:

```bash
docker build -t movies-app .
```

This command builds a containerized version of the application with all dependencies. The Dockerfile uses Python 3.11, installs PyTorch CPU-only 
(avoiding large NVIDIA/CUDA packages), and sets up the FastAPI server.

### Start the container
Run the container with your environment variables:

```bash
docker run -d --rm -p 8000:8000 --env-file .env --name movie-container movies-app
```

Breaking down this command:
- `--rm` - Automatically removes the container when it stops
- `-p 8000:8000` - Maps port 8000 from the container to your local machine
- `--env-file .env` - Loads your ScyllaDB credentials from the `.env` file
- `--name movie-container` - Names the container for easy reference
- `movies-app` - The image name from the previous build step

When the container starts, it automatically:
1. Runs the migration script ([src/migrate.py](https://github.com/scylladb/vector-search-examples/blob/main/movie-recommendation/src/migrate.py)) to create the keyspace, table, and vector index.
1. Starts the FastAPI server on port 8000

### Load sample data
With the container running, load the sample movie dataset:

```bash
docker exec movie-container python src/load_data.py
```

This ingests approximately 30,000 movies from the [TMDB dataset](https://www.kaggle.com/datasets/asaniczka/tmdb-movies-dataset-2023-930k-movies/). The data loading process:
1. Reads movie data from CSV files in `src/data/`
2. Generates 384-dimensional embeddings for each movie plot using the `all-MiniLM-L6-v2` model
3. Inserts movies with their embeddings into ScyllaDB

You'll see progress output:

```
⏳ Ingestion started...
📄 Ingesting sample data 1/3 ...
 55%|█████▍    | 5450/9999 [00:14<00:08, 518.68req/s]
```

The ingestion process takes a few minutes.

### Access the application
Once data loading completes, open your browser to:

**[http://127.0.0.1:8000](http://127.0.0.1:8000)**

You can now:
- Enter text descriptions to get movie recommendations (e.g., "a thriller about artificial intelligence")
- Browse the interactive API documentation at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Check application health at [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

The application uses vector similarity search to find movies whose plot embeddings are closest to your query embedding, returning semantically relevant recommendations.

Check the source code of the application for more details: https://github.com/scylladb/vector-search-examples

Or for the specific movie-recommendation folder:

https://github.com/scylladb/vector-search-examples/tree/main/movie-recommendation

## Understanding the database schema
When you run the Docker container, the migration script automatically creates the database schema. Here's what gets created in your ScyllaDB cluster:

```cql
CREATE KEYSPACE IF NOT EXISTS example_ks 
WITH replication = {'class': 'NetworkTopologyStrategy', 'replication_factor': '3'};

CREATE TABLE IF NOT EXISTS example_ks.movies (
    id INT,
    release_date TIMESTAMP,
    title TEXT,
    tagline TEXT,
    genre TEXT,
    imdb_id TEXT,
    poster_url TEXT,
    plot TEXT,
    plot_embedding VECTOR<FLOAT, 384>,
    PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ann_index ON example_ks.movies(plot_embedding) 
USING 'vector_index'
WITH OPTIONS = { 'similarity_function': 'DOT_PRODUCT' };
```

**Keyspace:**
- `CREATE KEYSPACE IF NOT EXISTS example_ks` - Creates a keyspace
- `'class': 'NetworkTopologyStrategy'` - Replication strategy
- `'replication_factor': '3'` - Data is replicated across 3 nodes for high availability
**Table:**
- `CREATE TABLE IF NOT EXISTS example_ks.movies` - Creates the movies table
- `plot_embedding VECTOR<FLOAT, 384>` - Vector column storing 384-dimensional float embeddings of movie plots (generated using [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) from Sentence Transformers)
- `PRIMARY KEY (id)` - Sets `id` as the primary key for data distribution


**Vector Index:**
```cql
CREATE INDEX IF NOT EXISTS ann_index ON example_ks.movies(plot_embedding) 
USING 'vector_index'
WITH OPTIONS = { 'similarity_function': 'DOT_PRODUCT' };
```

This creates an Approximate Nearest Neighbor (ANN) index on the `plot_embedding` vector column, enabling fast similarity search queries. The index uses `DOT_PRODUCT` as the similarity function to measure how closely vectors match. 

`DOT_PRODUCT` is optimal for this use case (and for LLM projects in general) because the [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) model produces normalized embeddings (vectors with length of 1). For normalized vectors, dot product is equivalent to cosine similarity but computationally faster, making it the best choice. Other available similarity functions include `COSINE` and `EUCLIDEAN`.
