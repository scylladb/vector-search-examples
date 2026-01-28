# ScyllaDB Semantic Search example

This example project shows you how to build a semantic search application with 
ScyllaDB Vector Search.

## Prerequisites
* [ScyllaDB Cloud](https://cloud.scylladb.com/) cluster with `vector search` enabled 
* You’ve read [Quick Start Guide to Vector Search](https://cloud.docs.scylladb.com/stable/vector-search/vector-search-quick-start.html)
* [Docker](https://docs.docker.com/get-docker/)

## Get started
1. Launch a new ScyllaDB cluster with `vector search` enabled
1. Clone repository and open the `movie-recommendation` folder:
    ```sh
    git clone https://github.com/scylladb/vector-search-examples.git
    cd vector-search-examples/movie-recommendation
    ```
1. Create a `.env` file based on the example and add your database credentials:
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
    SCYLLADB_KEYSPACE=example_ks
    ```

## Run the app with Docker
To run the application in Docker:

1. Build the Docker image:
    ```sh
    docker build -t movies-app .
    ```
1. Run the container (runs database migration and starts app server):
    ```sh
    docker run --rm -p 8000:8000 --env-file .env --name movie-container movies-app
    ```
1. Load sample data into the container:
    ```sh
    docker exec movie-container python src/load_data.py
    ```
    This starts loading the database with sample data:
    ```
    ⏳ Ingestion started...
    📄 Ingesting sample data 1/3 ...
     55%|█████▍    | 5450/9999 [00:14<00:08, 518.68req/s]
    ```
1. Open the app: http://127.0.0.1:8000/


## Run locally with Python
1. Install dependencies using UV:
    ```sh
    uv sync
    ```
1. Run the migration script to create a new keyspace and tables:
    ```sh
    uv run src/migrate.py
    ```
1. Ingest sample data:
    ```sh
    uv run src/load_data.py
    ```
1. Run the app:
    
    **Option A: Streamlit UI**
    ```sh
    uv run streamlit run streamlit_ui.py
    ```
    
    **Option B: FastAPI Server**
    ```sh
    uv run uvicorn src.main:app --reload --port 8000
    ```
    App will be available at `http://localhost:8000`
    - Interactive docs: `http://localhost:8000/docs`
    - Health check: `http://localhost:8000/health`

## Development

### Tech stack
- **Database**: [ScyllaDB](https://www.scylladb.com/) with Vector Search enabled
- **Backend**: [FastAPI](https://fastapi.tiangolo.com/)
- **Frontend**: [HTMX](https://htmx.org/)
- **Embeddings**: [Sentence Transformers](https://www.sbert.net/) (all-MiniLM-L6-v2)
- **Package Manager**: [UV](https://docs.astral.sh/uv/) - Fast Python package installer

### Project structure
```
movie-recommendation/
├── src/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── schemas.py           # Pydantic models for FastAPI
│   ├── migrate.py           # Database migration script
│   ├── load_data.py         # Data ingestion script
│   ├── routers/             # API endpoints
│   ├── movie_recommender/   # Recommendation engine (vector search)
│   ├── db/                  # ScyllaDB client and schema
│   ├── data/                # Sample movie data CSVs
│   ├── templates/           # Jinja2 HTML templates
│   └── static/              # Static assets (JS, CSS, images)
├── streamlit_ui.py          # Streamlit UI (optional)
├── pyproject.toml           # Project dependencies (UV)
├── requirements.txt         # Dependencies for Docker
├── .env.example             # Environment variables template
└── Dockerfile               # Container configuration
```


## Links
* [Step-by-step tutorial](https://vector-search.scylladb.com/stable/movie-recommendation.html)
* [ScyllaDB Docs](https://docs.scylladb.com/stable/)
