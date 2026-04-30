# Filtered vector search for RAG with ScyllaDB

This tutorial shows you how to scope retrieval in a RAG pipeline using **filtered vector search** in ScyllaDB.

Without filtering, a vector search query scans all stored embeddings and returns the most semantically similar results regardless of any metadata. For RAG, this is a problem: if a user asks *"recommend a horror movie from the 80s"*, an unfiltered search may surface results from the wrong genre or the wrong era, feeding irrelevant context to the LLM.

ScyllaDB solves this with **local vector indexes**: a per-partition HNSW index that restricts the search space to rows matching a partition key value before running ANN. The result is fast, scoped retrieval that gives the LLM only the context it needs.

In this tutorial, you'll extend the [movie recommendation](https://github.com/scylladb/vector-search-examples/tree/main/movie-recommendation) app to answer natural-language questions about movies, filtered by genre and by release decade.

Source code is [available on GitHub](https://github.com/scylladb/vector-search-examples/tree/main/movie-recommendation).

## Prerequisites

* [ScyllaDB Cloud account](https://cloud.scylladb.com/)
* [Python 3.11 or newer](https://www.python.org/downloads/)
* [Groq API key](https://console.groq.com/) (free tier is sufficient)

## Install Python requirements

1. Create and activate a virtual environment:
    ```
    virtualenv env && source env/bin/activate
    ```
1. Install dependencies:
    ```sh
    pip install scylla-driver pydantic sentence-transformers groq python-dotenv
    ```
    This installs:
    * **ScyllaDB Python driver**: connects to ScyllaDB with DC-aware load balancing
    * **Pydantic**: data validation and object handling
    * **Sentence Transformers**: creates embeddings from text
    * **Groq**: fast LLM inference for the generation step
    * **python-dotenv**: loads credentials from a `.env` file

## How filtered vector search works

ScyllaDB supports two kinds of vector indexes:

| | Global index | Local index |
|---|---|---|
| **Scope** | All rows in the table | Rows within one partition |
| **WHERE clause** | Requires `ALLOW FILTERING` | Uses the partition key — no `ALLOW FILTERING` |
| **Performance** | Slower — scans the entire index space | Fast — searches only the target partition's index |
| **RAG use case** | Cross-tenant full-corpus search | Per-user, per-genre, per-category scoped retrieval |

For RAG, **local indexes are almost always the right choice**. The filter column becomes the partition key, and ScyllaDB maintains a small, dedicated HNSW index for each partition value. Queries touch only the relevant shard.

## Set up ScyllaDB

### Create the schema

The schema has two tables:

* `movies` — global index for unfiltered search
* `movies_by_genre` — partitioned by `genre`, with a local index for filtered search

```sql
CREATE KEYSPACE IF NOT EXISTS example_ks
  WITH replication = {'class': 'NetworkTopologyStrategy', 'replication_factor': '3'};

-- Unfiltered search (global index)
CREATE TABLE IF NOT EXISTS example_ks.movies (
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

CREATE CUSTOM INDEX IF NOT EXISTS ann_index
  ON example_ks.movies(plot_embedding)
  USING 'vector_index'
  WITH OPTIONS = { 'similarity_function': 'DOT_PRODUCT' };

-- Filtered search by genre (local index)
CREATE TABLE IF NOT EXISTS example_ks.movies_by_genre (
    genre        TEXT,
    id           INT,
    release_date TIMESTAMP,
    title        TEXT,
    tagline      TEXT,
    imdb_id      TEXT,
    poster_url   TEXT,
    plot         TEXT,
    plot_embedding VECTOR<FLOAT, 384>,
    PRIMARY KEY (genre, id)
);

CREATE CUSTOM INDEX IF NOT EXISTS ann_index_by_genre
  ON example_ks.movies_by_genre((genre), plot_embedding)
  USING 'vector_index'
  WITH OPTIONS = { 'similarity_function': 'DOT_PRODUCT' };
```

`PRIMARY KEY (genre, id)` makes `genre` the partition key. The local index syntax `((genre), plot_embedding)` tells ScyllaDB to build a separate HNSW index for every distinct genre value.

### Connect to ScyllaDB

Create `scylladb.py`:

```python
from cassandra.cluster import Cluster, ExecutionProfile, EXEC_PROFILE_DEFAULT
from cassandra.policies import DCAwareRoundRobinPolicy, TokenAwarePolicy
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import dict_factory
import os
from dotenv import load_dotenv

load_dotenv()

class ScyllaClient:
    def __init__(self, keyspace: str = None):
        config = {
            "host": os.getenv("SCYLLADB_HOST"),
            "port": os.getenv("SCYLLADB_PORT", "9042"),
            "username": os.getenv("SCYLLADB_USERNAME", "scylla"),
            "password": os.getenv("SCYLLADB_PASSWORD"),
            "datacenter": os.getenv("SCYLLADB_DATACENTER"),
        }
        self.cluster = self._get_cluster(config)
        self.session = self.cluster.connect(keyspace or os.getenv("SCYLLADB_KEYSPACE"))

    def _get_cluster(self, config: dict) -> Cluster:
        profile = ExecutionProfile(
            load_balancing_policy=TokenAwarePolicy(
                DCAwareRoundRobinPolicy(local_dc=config["datacenter"])
            ),
            row_factory=dict_factory,
        )
        return Cluster(
            execution_profiles={EXEC_PROFILE_DEFAULT: profile},
            contact_points=[config["host"]],
            port=config["port"],
            auth_provider=PlainTextAuthProvider(
                username=config["username"],
                password=config["password"],
            ),
        )

    def get_session(self):
        return self.session

    def query_data(self, query, params=None):
        return self.session.execute(query, params or []).all()

    def shutdown(self):
        self.cluster.shutdown()
```

DC-aware load balancing is **required** for vector search — queries must be routed to the correct datacenter.

### Configure credentials

Create a `.env` file:

```
SCYLLADB_HOST=node-0.aws-us-east-1.xxxxxxxxxxx.clusters.scylla.cloud
SCYLLADB_PORT=9042
SCYLLADB_USERNAME=scylla
SCYLLADB_PASSWORD=your-password
SCYLLADB_DATACENTER=AWS_US_EAST_1
SCYLLADB_KEYSPACE=example_ks
GROQ_API_KEY=your-groq-api-key
```

### Run the migration

Create `migrate.py` and run it once to apply the schema:

```python
import os
from scylladb import ScyllaClient

client = ScyllaClient.__new__(ScyllaClient)
config = {
    "host": os.getenv("SCYLLADB_HOST"),
    "port": os.getenv("SCYLLADB_PORT", "9042"),
    "username": os.getenv("SCYLLADB_USERNAME", "scylla"),
    "password": os.getenv("SCYLLADB_PASSWORD"),
    "datacenter": os.getenv("SCYLLADB_DATACENTER"),
}
from cassandra.cluster import Cluster, ExecutionProfile, EXEC_PROFILE_DEFAULT
from cassandra.policies import DCAwareRoundRobinPolicy, TokenAwarePolicy
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import dict_factory
from dotenv import load_dotenv

load_dotenv()

profile = ExecutionProfile(
    load_balancing_policy=TokenAwarePolicy(
        DCAwareRoundRobinPolicy(local_dc=os.getenv("SCYLLADB_DATACENTER"))
    ),
    row_factory=dict_factory,
)
cluster = Cluster(
    execution_profiles={EXEC_PROFILE_DEFAULT: profile},
    contact_points=[os.getenv("SCYLLADB_HOST")],
    port=os.getenv("SCYLLADB_PORT", "9042"),
    auth_provider=PlainTextAuthProvider(
        username=os.getenv("SCYLLADB_USERNAME", "scylla"),
        password=os.getenv("SCYLLADB_PASSWORD"),
    ),
)
session = cluster.connect()

print("Applying schema...")
with open("schema.cql") as f:
    for statement in f.read().split(";"):
        statement = statement.strip()
        if statement:
            session.execute(statement)
print("Done.")
cluster.shutdown()
```

```sh
python migrate.py
```

## Build the retrieval module

### Pydantic models

Create `models.py`:

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class Movie(BaseModel):
    id: int
    title: Optional[str] = None
    release_date: Optional[datetime] = None
    tagline: Optional[str] = None
    genre: Optional[str] = None
    poster_url: Optional[str] = None
    imdb_id: Optional[str] = None
    plot: Optional[str] = None
    plot_embedding: Optional[list[float]] = None

class RecommendRequest(BaseModel):
    query: str = Field(..., description="Natural-language movie query")
    top_k: int = Field(default=5, ge=1, le=50)
    genre: Optional[str] = Field(default=None, description="Genre filter")
    decade: Optional[int] = Field(default=None, description="Release decade, e.g. 1980")
```

### Embedding creator

Create `embedding_creator.py`:

```python
from sentence_transformers import SentenceTransformer

class EmbeddingCreator:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name, device="cpu")

    def create_embedding(self, text: str) -> list[float]:
        return self.model.encode(text).tolist()
```

### Retrieval with filtering

Create `retriever.py`. This module exposes three retrieval strategies:

* **Unfiltered**: searches the global index across all movies
* **Genre-filtered**: uses the local index — fast, scoped to one genre partition
* **Genre + decade filtered**: uses the local index with an additional clustering column range filter on `release_date`

```python
from datetime import datetime
from scylladb import ScyllaClient
from embedding_creator import EmbeddingCreator
from models import Movie


class MovieRetriever:
    def __init__(self):
        self.db = ScyllaClient()
        self.embedder = EmbeddingCreator()

    def search(self, query: str, top_k: int = 5) -> list[Movie]:
        """Unfiltered ANN search across all movies."""
        vec = self.embedder.create_embedding(query)
        rows = self.db.query_data(
            """SELECT * FROM movies
               ORDER BY plot_embedding ANN OF %s
               LIMIT %s""",
            [vec, top_k],
        )
        return [Movie(**row) for row in rows]

    def search_by_genre(self, query: str, genre: str, top_k: int = 5) -> list[Movie]:
        """Local-index ANN search scoped to a single genre partition.

        ScyllaDB maintains a separate HNSW index for each genre value,
        so this query only searches within the 'genre' partition — no
        ALLOW FILTERING needed.
        """
        vec = self.embedder.create_embedding(query)
        rows = self.db.query_data(
            """SELECT * FROM movies_by_genre
               WHERE genre = %s
               ORDER BY plot_embedding ANN OF %s
               LIMIT %s""",
            [genre, vec, top_k],
        )
        return [Movie(**row) for row in rows]

    def search_by_genre_and_decade(
        self, query: str, genre: str, decade: int, top_k: int = 5
    ) -> list[Movie]:
        """Local-index ANN search scoped to genre + a release decade.

        The decade filter is applied as a range on the clustering column
        release_date after ScyllaDB narrows the search to the genre partition.
        Note: inequality range filters add some overhead — use only when the
        decade constraint is meaningful to the user's query.
        """
        vec = self.embedder.create_embedding(query)
        decade_start = datetime(decade, 1, 1)
        decade_end = datetime(decade + 10, 1, 1)
        rows = self.db.query_data(
            """SELECT * FROM movies_by_genre
               WHERE genre = %s
                 AND release_date >= %s
                 AND release_date < %s
               ORDER BY plot_embedding ANN OF %s
               LIMIT %s
               ALLOW FILTERING""",
            [genre, decade_start, decade_end, vec, top_k],
        )
        return [Movie(**row) for row in rows]
```

> **Why does the decade query need `ALLOW FILTERING`?**
> The genre partition key is fully specified, so ScyllaDB selects the right local index automatically. The additional `release_date` range is a clustering column filter that requires reading all index entries for that partition and post-filtering by date. `ALLOW FILTERING` is safe here because the search space is already bounded to a single partition — not the full table.

## Build the RAG module

The generation step receives the retrieved movie plots as context and uses Groq to produce a natural-language answer.

Create `rag.py`:

```python
import os
from groq import Groq
from models import Movie, RecommendRequest
from retriever import MovieRetriever

GROQ_MODEL = "llama-3.3-70b-versatile"

class MovieRAG:
    def __init__(self):
        self.retriever = MovieRetriever()
        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def _retrieve(self, request: RecommendRequest) -> list[Movie]:
        """Select the right retrieval strategy based on the filters provided."""
        if request.genre and request.decade:
            return self.retriever.search_by_genre_and_decade(
                request.query, request.genre, request.decade, request.top_k
            )
        if request.genre:
            return self.retriever.search_by_genre(
                request.query, request.genre, request.top_k
            )
        return self.retriever.search(request.query, request.top_k)

    def _build_context(self, movies: list[Movie]) -> str:
        parts = []
        for m in movies:
            parts.append(
                f"Title: {m.title}\n"
                f"Genre: {m.genre}\n"
                f"Year: {m.release_date.year if m.release_date else 'unknown'}\n"
                f"Plot: {m.plot}\n"
            )
        return "\n---\n".join(parts)

    def answer(self, request: RecommendRequest) -> str:
        movies = self._retrieve(request)
        if not movies:
            return "No matching movies found in the database."

        context = self._build_context(movies)
        prompt = (
            f"You are a movie expert. Use only the movies listed below to answer "
            f"the user's question. Do not invent movies.\n\n"
            f"Movies:\n{context}\n\n"
            f"User question: {request.query}"
        )

        response = self.groq.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful movie recommendation assistant."},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content
```

## Try it out

Create `main.py`:

```python
from models import RecommendRequest
from rag import MovieRAG

rag = MovieRAG()

# Unfiltered: searches all movies
print(rag.answer(RecommendRequest(query="a story about time travel and friendship")))

# Genre-filtered: local index, searches only within 'Science Fiction'
print(rag.answer(RecommendRequest(
    query="space exploration gone wrong",
    genre="Science Fiction",
)))

# Genre + decade: local index, further scoped to the 1980s
print(rag.answer(RecommendRequest(
    query="dystopian future controlled by machines",
    genre="Science Fiction",
    decade=1980,
)))
```

Run it:

```sh
python main.py
```

## Load sample data

Before querying, you need movies in both tables. Download the sample CSV and ingest it:

```sh
wget https://github.com/scylladb/vector-search-examples/raw/refs/heads/main/movie-recommendation/data/movies_sample.csv
```

Create `ingest.py`:

```python
import csv
import ast
from datetime import datetime
from scylladb import ScyllaClient
from embedding_creator import EmbeddingCreator

DATE_FORMAT = "%Y-%m-%d"

class MovieLoader:
    def __init__(self):
        self.db = ScyllaClient()
        self.embedder = EmbeddingCreator()

    def _prepare_row(self, row: dict) -> dict | None:
        try:
            release_date = datetime.strptime(row["release_date"].strip(), DATE_FORMAT)
            embedding = ast.literal_eval(row["plot_embedding"])
        except (ValueError, SyntaxError):
            return None
        return {
            "id": int(row["id"]),
            "release_date": release_date,
            "title": row["title"],
            "tagline": row["tagline"],
            "genre": row["genres"],
            "poster_url": row["poster_path"],
            "imdb_id": row["imdb_id"],
            "plot": row["overview"],
            "plot_embedding": embedding,
        }

    def ingest(self, csv_file: str):
        session = self.db.get_session()
        movies_stmt = session.prepare(
            "INSERT INTO movies (id, release_date, title, tagline, genre, "
            "poster_url, imdb_id, plot, plot_embedding) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        genre_stmt = session.prepare(
            "INSERT INTO movies_by_genre (genre, id, release_date, title, tagline, "
            "poster_url, imdb_id, plot, plot_embedding) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )

        with open(csv_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                data = self._prepare_row(row)
                if not data:
                    continue
                # Insert into both tables
                session.execute(movies_stmt, (
                    data["id"], data["release_date"], data["title"], data["tagline"],
                    data["genre"], data["poster_url"], data["imdb_id"],
                    data["plot"], data["plot_embedding"],
                ))
                session.execute(genre_stmt, (
                    data["genre"], data["id"], data["release_date"], data["title"],
                    data["tagline"], data["poster_url"], data["imdb_id"],
                    data["plot"], data["plot_embedding"],
                ))

        print("Ingestion complete.")

if __name__ == "__main__":
    MovieLoader().ingest("movies_sample.csv")
```

```sh
python ingest.py
```

## Schema design guidelines

When designing a filtered vector search schema for RAG, keep these rules in mind:

**Make your filter column the partition key.** ScyllaDB builds a separate local HNSW index per partition. Queries that supply the full partition key bypass the global index entirely and search only the relevant shard.

**Use local indexes over global indexes.** A global index query with a `WHERE` clause uses `ALLOW FILTERING` and scans the entire index space before post-filtering. A local index query scopes the ANN search to one partition upfront — orders of magnitude faster at scale.

**Avoid high-cardinality partition keys.** A partition key like `user_id` with millions of distinct values creates millions of tiny indexes. Group by category, tenant, or time bucket instead.

**Use clustering columns for secondary filters.** Range filters on clustering columns (like `release_date`) work well as a second-level filter within a partition. They add some overhead but do not require a full-table scan.

**Match the embedding model at index time and query time.** Vectors from different models live in incompatible spaces. Switching models requires re-embedding and re-ingesting all rows.
