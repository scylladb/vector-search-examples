# ScyllaDB Vector Search example

This example shows you how to build a vector search application with ScyllaDB.

You'll build a simple movie recommendation app that takes a text input from the user and performs vector search to recommend a movie to watch.

## Prerequisites
* Sign up for [ScyllaDB Cloud](https://cloud.scylladb.com/)
* Python 3.9+
* [UV package manager](https://docs.astral.sh/uv/)

## Get started
1. Launch a new ScyllaDB cluster with `vector search` enabled
1. Clone repository and open the `movie-recommendation` folder:
    ```sh
    git clone https://github.com/scylladb/vector-search-examples.git
    cd vector-search-examples/movie-recommendation
    ```
1. Install dependencies using UV:
    ```sh
    uv sync
    ```
1. Create a `.env` file from the example and add your database credentials:
    ```sh
    cp .env.example .env
    ```
    Then edit `.env` with your ScyllaDB cluster details:
    ```env
    SCYLLADB_HOST=node-0.aws-us-east-1.xxxxxxx.clusters.scylla.cloud
    SCYLLADB_PORT=9042
    SCYLLADB_USERNAME=scylla
    SCYLLADB_PASSWORD=xxxxxxxxx
    SCYLLADB_DATACENTER=AWS_US_EAST_1
    SCYLLADB_KEYSPACE=recommend
    ```
1. Run the migration script to create a new keyspace and tables:
    ```sh
    uv run python db/migrate.py 
    ```
1. Ingest sample data (~30k movies from this [dataset](https://www.kaggle.com/datasets/asaniczka/tmdb-movies-dataset-2023-930k-movies/)):
    ```sh
    uv run python ingest.py
    ```
1. Run the app:
    
    **Option A: Streamlit UI**
    ```sh
    uv run streamlit run streamlit_ui.py
    ```
    
    **Option B: FastAPI Server**
    ```sh
    uv run uvicorn main:app --reload --port 8000
    ```
    API will be available at `http://localhost:8000`
    - Interactive docs: `http://localhost:8000/docs`
    - Health check: `http://localhost:8000/health`

## API Usage

**Endpoint:** `POST /api/v1/recommend`

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "a movie about space exploration",
    "top_k": 5
  }'
```

**Response:**
```json
{
  "movies": [
    {
      "id": 123,
      "title": "Interstellar",
      "release_date": "2014-11-07T00:00:00",
      "tagline": "Mankind was born on Earth. It was never meant to die here.",
      "genre": "Science Fiction",
      "poster_url": "/poster.jpg",
      "imdb_id": "tt0816692",
      "plot": "A team of explorers travel through a wormhole..."
    }
  ],
  "count": 5
}
```

![movies app](../docs/source/_static/img/recommend_movies.png)

## Models
* embedding model (runs locally): [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)

## Links
* [Step-by-step tutorial](https://vector-search.scylladb.com/stable/movie-recommendation.html)
* [ScyllaDB Docs](https://docs.scylladb.com/stable/)