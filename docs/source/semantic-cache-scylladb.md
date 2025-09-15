# Build a semantic cache layer with ScyllaDB

This tutorial shows you how to build a **semantic cache layer** using OpenAI and ScyllaDB.

Semantic caching allows you to reuse previous responses by matching new queries to semantically similar ones, reducing redundant LLM API calls, lowering costs, and improving response times.

Source code is [available on GitHub](https://github.com/scylladb/vector-search-examples/tree/main/semantic-cache).

## Prerequisites
* [ScyllaDB Cloud account](https://cloud.scylladb.com/)
* [Python 3.9 or newer](https://www.python.org/downloads/)

## Install Python requirements
1. Create and activate a new Python virtual environment:
    ```
    virtualenv env && source env/bin/activate
    ```
1. Install requirements:
    ```
    pip install scylla-driver sentence-transformers openai
    ```
    This installs:
    * ScyllaDB Python driver
    * HuggingFace Sentence Transformers
    * OpenAI API library

## Set up ScyllaDB as a vector store
1. Create a new ScyllaDB Cloud instance with `vector search` enabled.
1. Create `config.py` and add your database connection details (host, username, password, etc...):
    ```py
    SCYLLADB_CONFIG = {
        "host": "node-0.aws-us-east-1.xxxxxxxxxxx.clusters.scylla.cloud",
        "port": "9042",
        "username": "scylla",
        "password": "passwd",
        "datacenter": "AWS_US_EAST_1",
        "keyspace": "semantic_cache"
    }
    ```
1. Create `schema.cql`:
    ```
    CREATE KEYSPACE semantic_cache WITH replication = {'class': 'NetworkTopologyStrategy', 'replication_factor': '3'}
    AND TABLETS = {'enabled': 'false'};

    CREATE TABLE semantic_cache.prompts (
        prompt_id uuid PRIMARY KEY,
        inserted_at timestamp,
        prompt_text text,
        prompt_embedding vector<float, 384>,
        llm_response text,
        updated_at timestamp
    );

    CREATE INDEX IF NOT EXISTS ann_index ON semantic_cache.prompts(prompt_embedding) 
    USING 'vector_index'
    WITH OPTIONS = { 'similarity_function': 'DOT_PRODUCT' };
    ```
1. Create a helper module called `scylladb.py` to insert data, and query results from ScyllaDB:
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
1. Create and run `migrate.py`script:
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
    This migration script creates a keyspace, a table for cached responses, and a vector index for similarity search in ScyllaDB.

## Build the app
In this step, you'll build a semantic caching app that saves new responses and retrieves them later when similar questions are asked.

ScyllaDB acts as a persistent caching layer for LLM responses, enabling faster and less expensive operations when working with LLM APIs.

1. Create new class:
    ```py
    class ScyllaSemanticCacheApp:
        def __init__(self):
            self.scylla_client = ScyllaClient()
            self.openai_client = OpenAI(base_url=OPENAI_API["base_url"],
                                        api_key=OPENAI_API["apikey"])
            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    ```
1. Create function to create embedding:
    ```py
    def create_embedding(self, text):
        return self.embedding_model.encode(text).tolist()
    ```
1. Create function to query OpenAI:
    ```python
    def ask_openai(self, prompt):
        completion = self.openai_client.chat.completions.create(
        model="openai/gpt-4.1-nano",
        messages=[{
            "role": "user",
            "content": prompt
            }],
        )
        return completion.choices[0].message.content
    ```
1. Check if a semantically similar prompt already exists in the cache.
    ```py
    def calc_cosine_similarity(self, vec1, vec2):
        v1, v2 = np.array(vec1), np.array(vec2)
        return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

    def search_cache(self, embedding, threshold=0.80):
        k = 1
        cql = "SELECT * FROM prompts ORDER BY prompt_embedding ANN OF %s LIMIT %s;"
        results = self.scylla_client.query_data(cql, [embedding, k])
        if len(results) > 0:
            cached_response = results[0]
            similarity = self.calc_cosine_similarity(embedding, cached_response['prompt_embedding'])
            if similarity >= threshold:
                return cached_response['llm_response']
        return None
    ```
    * Uses ScyllaDB’s Approximate Nearest Neighbor (ANN) search.
    * Calculates cosine similarity between embeddings.
    * Returns cached response if similarity ≥ 0.80.
1. Store the response if this is a new query and cannot be served by cache:
    ```py
    def insert_to_cache(self, prompt_text, prompt_embedding, llm_response):
        data = {
            "prompt_id": uuid.uuid4(),
            "prompt_text": prompt_text,
            "prompt_embedding": prompt_embedding,
            "llm_response": llm_response,
            "inserted_at": datetime.now()
        }
        self.scylla_client.insert_data("prompts", data)
    ```
1. Finally, putting it all together in a function:
    ```py
    def semantic_cached_prompt(self, prompt):
        embedding = self.create_embedding(prompt)
        cached_response = self.search_cache(embedding, threshold=0.80)

        if cached_response:
            print("Cache hit! Returning cached response...")
            return cached_response
        else:
            print("Cache miss... sending request to OpenAI!")
            response = self.ask_openai(prompt)
            self.insert_to_cache(prompt, embedding, response)
            return response
    ```
1. Test the app:
    ```py
    if __name__ == "__main__":
        app = ScyllaSemanticCacheApp()
        
        # First query, cache miss
        question = "What is the capital city of France?"
        print("Question 1:", question)
        answer = app.semantic_cached_prompt(question)
        print("\nAnswer (comes from LLM):", answer)
        
        # Second query, cache hit
        question = "What's the capital of France?"
        print("\nQuestion 2:", question)
        answer = app.semantic_cached_prompt(question)
        print("\nAnswer (comes from cache):", answer)
    ```

The complete semantic caching application is available on [GitHub](https://github.com/scylladb/vector-search-examples/tree/main/semantic-cache).

## Relevant resources
* [ScyllaDB Cloud](https://cloud.scylladb.com/)
* [ScyllaDB Documentation](https://docs.scylladb.com/)
