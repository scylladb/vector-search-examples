# ScyllaDB semantic cache example

This example application demonstrates how to build a semantic cache layer using ScyllaDB.

Semantic caching allows users to save and reuse answers from past queries, speeding up results and reducing LLM costs.

## Prerequisites
* Sign up for [ScyllaDB Cloud](https://cloud.scylladb.com/)
* * OpenAI API key (using [OpenAI](https://openai.com/api/) or [OpenRouter](https://openrouter.ai/))
* [Docker](https://docs.docker.com/engine/install/) installed
* Open
* Python

## Setup

### 1. Database setup
1. Launch a new ScyllaDB cluster with `vector search` enabled
1. Clone repository and open the rag example folder:
    ```sh
    git clone https://github.com/scylladb/vector-search-examples.git
    cd vector-search-examples/semantic-cache
    ```
1. Open a terminal window and save the database credentials as variables:
    ```sh
    SCYLLA_HOST="node-0.aws-us-east-1.xxxxxxxxxx.clusters.scylla.cloud" \
    SCYLLA_PORT="9042" \
    SCYLLA_USER="scylla" \
    SCYLLA_PASS="mypassword" \
    SCYLLA_DC="AWS_US_EAST_1"
    ```
    Save your OpenAI credentials as well:
    ```sh
    OPENAI_APIKEY="my_apikey" \
    OPENAI_BASE_URL="https://openrouter.ai/api/v1"
    ```

1. Install CQLSH:
    ```sh
    pip install scylla-cqlsh
    ```
1. Create schema (keyspace, table, vector index):
    ```sh
    cqlsh $SCYLLA_HOST $SCYLLA_PORT -u $SCYLLA_USER -p $SCYLLA_PASS -f schema.cql
    ```

### 2. App setup
1. Build image of the app:
    ```sh
    docker build -t scylla_semantic .
    ```
1. Run container and add credentials as `ENV` variables:
    ```sh
    docker run --rm -d \
        --name scylla_semantic_app \
        -e scylla_host="$SCYLLA_HOST" \
        -e scylla_port="$SCYLLA_PORT" \
        -e scylla_user="$SCYLLA_USER" \
        -e scylla_password="$SCYLLA_PASS" \
        -e scylla_datacenter="$SCYLLA_DC" \
        -e OPENAI_APIKEY="$OPENAI_APIKEY" \
        -e OPENAI_BASE_URL="$OPENAI_BASE_URL" \
        scylla_semantic
    ```
1. Run the app:
    ```sh
    docker exec -it scylla_semantic_app python scylla_semantic_cache.py
    ```
    ```
    Question 1: What is the capital city of France?
    Answer (comes from LLM): Paris
    Question 2: What's the capital of France?
    Answer (comes from cache): Paris
    ```

## Models
* embedding model (runs locally): [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
* language model (runs using API): [OpenAI GPT-4.1-nano](https://platform.openai.com/docs/models/gpt-4.1-nano)


## Links
* [Step-by-step tutorial](https://vector-search.scylladb.com/stable/rag-chatbot-scylladb.html)
* [ScyllaDB Docs](https://docs.scylladb.com/stable/)

