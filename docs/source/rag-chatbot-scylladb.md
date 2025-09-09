# Build a RAG chatbot with ScyllaDB

This tutorial shows you how to build a **Retrieval-Augmented Generation (RAG)** chatbot using ScyllaDB, Ollama, and LlamaIndex.

The chatbot runs in your terminal and lets you ask questions about ScyllaDB documentation.

Source code is available on GitHub.

## Prerequisites
* [ScyllaDB Cloud account](https://cloud.scylladb.com/)
* [Python 3.9 or newer](https://www.python.org/downloads/)

## Install Python requirements
1. Create and activate a new Python virtual environment.:
    ```
    virtualenv env && source env/bin/activate
    ```
1. Install requirements:
    ```
    pip install -r requirements.txt
    ```
    Including:
    * ScyllaDB Python driver
    * LlamaIndex
    * Ollama
    * SpaCy

## Set up ScyllaDB as a vector store
1. Create a new ScyllaDB Cloud instance with `vector search` enabled.
1. Create `config.py` and add your database connection details (hosts, username, password, etc...):
    ```py
    SCYLLADB_CONFIG = {
        "hosts": ["node-0.aws-us-east-1.xxxxxxxxxxx.clusters.scylla.cloud",
                "node-1.aws-us-east-1.xxxxxxxxxxx.clusters.scylla.cloud",
                "node-2.aws-us-east-1.xxxxxxxxxxx.clusters.scylla.cloud"],
        "port": "9042",
        "username": "scylla",
        "password": "passwd",
        "datacenter": "AWS_US_EAST_1",
        "keyspace": "rag"
    }
    ```
1. Create `migrate.py`:
    ```py
    import os
    from scylladb import ScyllaClient

    client = ScyllaClient()
    session = client.get_session()

    def absolute_file_path(relative_file_path):
        current_dir = os.path.dirname(__file__)
        return os.path.join(current_dir, relative_file_path)

    print("Creating keyspace and tables...")
    with open(absolute_file_path("schema.cql"), "r") as file:
        for query in file.read().split(";"):
            if len(query) > 0:
                session.execute(query)
    print("Migration completed.")

    client.shutdown()
    ```
    This migration script creates a keyspace, a table for text chunks and embeddings, and a vector index for similarity search in ScyllaDB:
    ```
    CREATE KEYSPACE rag WITH replication = {'class': 'NetworkTopologyStrategy', 'replication_factor': '3'} AND TABLETS = {'enabled': 'false'};

    CREATE TABLE rag.chunks (
        chunk_id UUID PRIMARY KEY,
        text TEXT,
        embedding vector<float, 768>
    ) WITH cdc = {'enabled': 'true'};


    CREATE INDEX IF NOT EXISTS ann_index ON rag.chunks(embedding)
    USING 'vector_index'
    WITH OPTIONS = { 'similarity_function': 'DOT_PRODUCT' };
    ```


## Download documentation files from GitHub

For this example, you will use documentation stored in the ScyllaDB [GitHub repository](https://github.com/scylladb/scylladb/tree/master/docs) (`.md` and `.rst` files).

1. Create a shell script (`./download_docs.sh`) to download files only from the `scylladb/docs` folder:
    ```sh
    git clone --no-checkout --depth=1 --filter=tree:0 \
    https://github.com/scylladb/scylladb.git
    cd scylladb
    git sparse-checkout set --no-cone /docs
    git checkout
    ```

After running this script, the documents will be saved in `scylladb/docs` folder locally. This folder will be used by the RAG ingestion component in the next step.

---

## Build a complete RAG application
In this step, you'll build a complete RAG application including loading documents, chunking, embedding, storing, and retrieval.

### 1. ScyllaDB client
ScyllaDB acts as a persistent store for the document chunk embeddings, enabling scalable vector storage and semantic search.

1. Create a helper module called `scylladb.py` to insert data, and query results ScyllaDB:
    ```py
    from cassandra.cluster import Cluster, ExecutionProfile, EXEC_PROFILE_DEFAULT
    from cassandra.policies import DCAwareRoundRobinPolicy, TokenAwarePolicy
    from cassandra.auth import PlainTextAuthProvider
    from cassandra.query import dict_factory
    import config

    class ScyllaClient():
        
        def __init__(self):
            scylla_config = config.SCYLLADB_CONFIG
            self.cluster = self._get_cluster(scylla_config)
            self.session = self.cluster.connect(scylla_config["keyspace"])
            
        def __enter__(self):
            return self
        
        def __exit__(self, exc_type, exc_value, traceback):
            self.shutdown()
            
        def shutdown(self):
            self.cluster.shutdown()

        def _get_cluster(self, config: dict) -> Cluster:
            profile = ExecutionProfile(
                load_balancing_policy=TokenAwarePolicy(
                        DCAwareRoundRobinPolicy(local_dc=config["datacenter"])
                    ),
                    row_factory=dict_factory
                )
            return Cluster(
                execution_profiles={EXEC_PROFILE_DEFAULT: profile},
                contact_points=config["hosts"],
                port=config["port"],
                auth_provider = PlainTextAuthProvider(username=config["username"],
                                                    password=config["password"]))
        
        def print_metadata(self):
            for host in self.cluster.metadata.all_hosts():
                print(f"Datacenter: {host.datacenter}; Host: {host.address}; Rack: {host.rack}")
        
        def get_session(self):
            return self.session
        
        def insert_data(self, table, data: dict):
            columns = list(data.keys())
            values = list(data.values())
            insert_query = f"""
            INSERT INTO {table} ({','.join(columns)}) 
            VALUES ({','.join(['%s' for c in columns])});
            """
            self.session.execute(insert_query, values)
            
        def query_data(self, query, values=[]):
            rows = self.session.execute(query, values)
            return rows.all()
    ```

### 2. Document ingestion
1. Create a file called `scylla_rag.py` with the following content:
    ```py
    from llama_index.core.node_parser import (
        SemanticDoubleMergingSplitterNodeParser,
        LanguageConfig,
    )
    from llama_index.core import SimpleDirectoryReader

    class ScyllaRag():
    ```
1. Add the `create_chunks()` function and implement document loading first:
   ```py
        def create_chunks(self, dir_path: str, files_limit=1):
            documents = SimpleDirectoryReader(input_dir=dir_path,
                                            recursive=True,
                                            num_files_limit=files_limit,
                                            required_exts=[".md", ".rst"],
                                            exclude_empty=True,
                                            exclude_hidden=True).load_data()
            # Filter out docs with no text
            documents = [doc for doc in documents if doc.text.strip()]
    ```
1. Then split the documents into semantically meaningful chunks:
    ```py
        def create_chunks(self, dir_path: str, files_limit=1):
            documents = SimpleDirectoryReader(input_dir=dir_path,
                                            recursive=True,
                                            num_files_limit=files_limit,
                                            required_exts=[".md", ".rst"],
                                            exclude_empty=True,
                                            exclude_hidden=True).load_data()
            # Filter out docs with no text
            documents = [doc for doc in documents if doc.text.strip()]

            splitter = SemanticDoubleMergingSplitterNodeParser(
                language_config=LanguageConfig(spacy_model="en_core_web_md"),
                initial_threshold=0.4, # merge sentences to create chunks
                appending_threshold=0.5, # merge chunk to the following sentence
                merging_threshold=0.5, # merge chunks to create bigger chunks
                max_chunk_size=2048,    
            )
            return splitter.get_nodes_from_documents(documents, show_progress=True)
    ```

### 3. Embedding generation
1. Add a function that turns a text chunk into embedding uising Ollama:
    ```py
    import ollama
    EMBEDDING_MODEL = "hf.co/CompendiumLabs/bge-base-en-v1.5-gguf"
    def create_embedding(self, content):
        return ollama.embed(model=self.EMBEDDING_MODEL, input=content)["embeddings"][0]
    ```
1. Add function that inserts each chunk and its embedding into the ScyllaDB table created earlier:
    ```py
    def vectorize(self, nodes, target_table: str):
        db_client = ScyllaClient()
        for node in nodes:
            chunk_id = uuid.uuid4()
            text = node.get_content()
            embedding = self.create_embedding(text)
            db_client.insert_data(target_table, {"text": text,
                                                "chunk_id": chunk_id,
                                                "embedding": embedding})
    ```

### 4. Retrieval and semantic search
1. Implement function that searches ScyllaDB for the most relevant chunks based on the user question:
    ```py
    def fetch_chunks(self, table: str, user_query: str, top_k=5):
        db_client = ScyllaClient()
        user_query_embedding = self.create_embedding(user_query)
        db_query = f"""SELECT chunk_id, text
                    FROM {table} 
                    ORDER BY embedding ANN OF %s LIMIT %s;
                   """
        values = [user_query_embedding, top_k]
        return db_client.query_data(db_query, values)
    ```
1. Add function that executes the request towards the LLM (combining the user’s question with the retrieved chunks):
    ```py
    def query_llm(self, user_query: str, chunks: list[str]) -> str:
        context = ""
        for i, chunk in enumerate(chunks):
            context += f"\n\n Item {i+1}: {chunk}"
        system_prompt = f"""You are an AI assistant that answers user 
        questions by combining your reasoning ability with the information 
        provided below: \n
        {context}
        """
        stream = ollama.chat(
            model=self.LANGUAGE_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query},
            ],
            stream=True,
        )
        print("Chatbot response:")
        for chunk in stream:
            print(chunk["message"]["content"], end="", flush=True)
    ```
1. Finally, putting it all toghether:
    ```py
    if __name__ == "__main__":
        scylla_rag = ScyllaRag()

        # ingest documents (only needs to run once)
        # nodes = scylla_rag.create_chunks("../scylladb/docs", files_limit=200)
        # scylla_rag.vectorize(nodes, target_table="rag.chunks")

        user_input = input("What do you want to know about ScyllaDB? ")
        
        nodes = scylla_rag.fetch_chunks("rag.chunks", user_input, top_k=3)
    
        chunks = [node['chunk_id'] for node in nodes]
        print("Retrieved chunks:", chunks)
    
        scylla_rag.query_llm(user_input, [node["text"] for node in nodes])
    ```

The complete RAG application file is available on GitHub.

## Relevant resources
* ScyllaDB docs
* Ollama
* LlamaIndex
