# ScyllaDB retrieval augmented generation (RAG) example

This example application demonstrates how to build a Retrieval-Augmented Generation (RAG) app using ScyllaDB.

The chatbot allows users to ask questions about ScyllaDB, retrieves relevant chunks from the official docs, and generates contextual answers using a local LLM.

## Tech stack

* [ScyllaDB Cloud](https://cloud.scylladb.com/): high-performance NoSQL database for storing vectors and performing semantic search
* [LlamaIndex](https://docs.llamaindex.ai/en/stable/): splitting documents into chunks
* [Ollama](https://ollama.com/): model downloads and text embedding
* Local models
    * embedding model: https://huggingface.co/CompendiumLabs/bge-base-en-v1.5-gguf
    * language model: https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF
    * Both models are small, so you should be able to run them even on modest hardware.

## Prerequisites
* Sign up for [ScyllaDB Cloud](https://cloud.scylladb.com/)
* [Docker](https://docs.docker.com/engine/install/) installed
* Python

## Setup

### 1. Database setup
1. Launch a new ScyllaDB cluster with `vector search` enabled
1. Clone repository and open the rag example folder:
    ```sh
    git clone https://github.com/scylladb/vector-search-examples.git
    cd vector-search-examples/rag-chatbot/
    ```
1. Open a terminal window and save the database credentials as variables:
    ```sh
    SCYLLA_HOST="node-0.aws-us-east-1.xxxxxxxxxx.clusters.scylla.cloud" \
    SCYLLA_PORT="9042" \
    SCYLLA_USER="scylla" \
    SCYLLA_PASS="mypassword" \
    SCYLLA_DC="AWS_US_EAST_1"
    ```
1. Install CQLSH:
    ```sh
    pip install scylla-cqlsh
    ```
1. Create schema (keyspace, table, vector index):
    ```sh
    cqlsh $SCYLLA_HOST $SCYLLA_PORT -u $SCYLLA_USER -p $SCYLLA_PASS -f schema.cql
    ```

### 2. Ollama setup
1. Create Docker network:
    ```sh
    docker network create scylla_rag_network
    ```
1. Start Ollama service:
    ```sh
    docker run -d \
        --network scylla_rag_network \
        -v ollama:/root/.ollama \
        --name ollama \
        ollama/ollama
    ```

### 3. RAG app setup
1. Build image of the rag app:
    ```sh
    docker build -t scylla_rag .
    ```
1. Run container and add database credentials as `ENV` variables:
    ```sh
    docker run --rm -d \
        --network scylla_rag_network \
        --name scylla_rag_app \
        -e scylla_host="$SCYLLA_HOST" \
        -e scylla_port="$SCYLLA_PORT" \
        -e scylla_user="$SCYLLA_USER" \
        -e scylla_password="$SCYLLA_PASS" \
        -e scylla_datacenter="$SCYLLA_DC" \
        scylla_rag
        
    ```

### 4. Load sample data
1. Load sample data into ScyllaDB:
    ```sh
    docker exec -it scylla_rag_app python insert_sample.py
    ```

### 5. Run the app
1. Start the chatbot:
    ```sh
    docker exec -it scylla_rag_app python scylla_rag.py
    ```

    ```
    Enter your question: What's ScyllaDB?
    ---
    Retrieved chunk IDs: ['5d460612-583b-4eca-96b5-770046d769dc', 'e3b2028f-6d93-4bdf-9fd0-c6d9fec851ac', '4c632adc-8a18-4bd3-bbdd-210e1d921112']
    Chatbot response:
    ScyllaDB is a low latency distributed NoSQL database [...]
    ```

## Links
* [Step-by-step tutorial](https://vector-search.scylladb.com/stable/rag-chatbot-scylladb.html)
* [ScyllaDB Docs](https://docs.scylladb.com/stable/)

