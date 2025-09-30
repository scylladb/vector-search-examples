# ScyllaDB Vector Search example

This example shows you how to build a vector search application with ScyllaDB.

You'll build a simple movie recommendation app that takes a text input from the user and performs vector search to recommend a movie to watch.

## Prerequisites
* Sign up for [ScyllaDB Cloud](https://cloud.scylladb.com/)
* Python 3.9+

## Get started
1. Launch a new ScyllaDB cluster with `vector search` enabled
1. Clone repository and open the `movie-recommendation` folder:
    ```sh
    git clone https://github.com/scylladb/vector-search-examples.git
    cd vector-search-examples/movie-recommendation
    ```
1. Create and activate a new Python virtual environment (you can use [virtualenv](https://virtualenv.pypa.io/en/latest/), [Poetry](https://python-poetry.org/docs/), [venv](https://docs.python.org/3/library/venv.html) or any other environment management library):
    ```
    virtualenv env && source env/bin/activate
    ```
1. Install requirements:
    ```sh
    pip install requirements.txt
    ```
1. Open `config.py` and add your database credentials:
    ```py
    SCYLLADB_CONFIG = {
        "host": "node-0.aws-us-east-1.xxxxxxx.clusters.scylla.cloud",
        "port": "9042",
        "username": "scylla",
        "password": "xxxxxxxxx",
        "datacenter": "AWS_US_EAST_1",
        "keyspace": "recommend"
    }
    ```
1. Ingest sample data (100k movies from this [dataset](https://www.kaggle.com/datasets/asaniczka/tmdb-movies-dataset-2023-930k-movies/)):
    ```sh
    python ingest.py
    ```
1. Run the app:
    ```sh
    streamlit run app.py
    ```

![movies app](_static/img/recommend_movies.png)

## Models
* embedding model (runs locally): [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)

## Links
* [Step-by-step tutorial](https://vector-search.scylladb.com/stable/movie-recommendation.html)
* [ScyllaDB Docs](https://docs.scylladb.com/stable/)