"""
Minimal mem0 example using ScyllaDB Cloud as the vector store backend.

Prerequisites:
  - A ScyllaDB Cloud cluster (vector search enabled)
  - Credentials in a .env file (see .env for required keys)
  - A Groq API key in .env

mem0 uses ScyllaDB's native vector search (HNSW ANN index on a vector column).
scylla-driver (shard-aware drop-in for cassandra-driver) handles the connection
with DC-aware load balancing — required for ScyllaDB Cloud.
Embeddings are generated locally via sentence-transformers (no API key needed).

Quick start:
  uv run main.py
"""

import os
from dotenv import load_dotenv
from cassandra.policies import DCAwareRoundRobinPolicy
from mem0 import Memory

# ---------------------------------------------------------------------------
# Load environment
# ---------------------------------------------------------------------------

load_dotenv()

SCYLLADB_ADDRESS    = os.environ["SCYLLADB_ADDRESS"]
SCYLLADB_USERNAME   = os.environ["SCYLLADB_USERNAME"]
SCYLLADB_PASSWORD   = os.environ["SCYLLADB_PASSWORD"]
SCYLLADB_DATACENTER = os.environ.get("SCYLLADB_DATACENTER", "AWS_US_EAST_1")
GROQ_API_KEY        = os.environ["GROQ_API_KEY"]

KEYSPACE = "mem0"
TABLE    = "memories"

# ---------------------------------------------------------------------------
# mem0 configuration
# mem0 builds the scylla-driver Session internally from these fields.
# load_balancing_policy is passed through to the driver — DC-aware routing
# is mandatory for ScyllaDB Cloud.
# ---------------------------------------------------------------------------

config = {
    "vector_store": {
        "provider": "cassandra",
        "config": {
            "contact_points": [SCYLLADB_ADDRESS],
            "port": 9042,
            "username": SCYLLADB_USERNAME,
            "password": SCYLLADB_PASSWORD,
            "keyspace": KEYSPACE,
            "collection_name": TABLE,
            "load_balancing_policy": DCAwareRoundRobinPolicy(local_dc=SCYLLADB_DATACENTER),
            # all-MiniLM-L6-v2 → 384 dims
            "embedding_model_dims": 384,
        },
    },
    "llm": {
        "provider": "groq",
        "config": {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "api_key": GROQ_API_KEY,
        },
    },
    "embedder": {
        "provider": "huggingface",
        "config": {
            "model": "sentence-transformers/all-MiniLM-L6-v2",
        },
    },
    # Minimal extraction prompt — drastically reduces tokens per call.
    # The default mem0 prompt is ~8k tokens; this keeps it under 200.
    "custom_prompt": (
        "Extract concise facts from the input as a JSON list: "
        '{\"facts\": [\"<fact1>\", \"<fact2>\", ...]}. '
        "Only include facts explicitly stated. Return valid JSON only."
    ),
}

# ---------------------------------------------------------------------------
# Initialise mem0
# ---------------------------------------------------------------------------

m = Memory.from_config(config)
USER_ID = "alice"

# ---------------------------------------------------------------------------
# Add memories
# ---------------------------------------------------------------------------

print("=== Adding memories ===")

result = m.add(
    "I love hiking in the mountains, especially in autumn.",
    user_id=USER_ID,
)
print("add():", result)

result = m.add(
    [
        {"role": "user",      "content": "What's a good pasta recipe?"},
        {"role": "assistant", "content": "Try cacio e pepe — it only needs three ingredients."},
        {"role": "user",      "content": "I'm vegetarian, by the way."},
    ],
    user_id=USER_ID,
)
print("add() conversation:", result)

# ---------------------------------------------------------------------------
# Search memories
# ---------------------------------------------------------------------------

print("\n=== Searching memories ===")

results = m.search("outdoor activities", filters={"user_id": USER_ID}, limit=3)
for entry in results["results"]:
    print(f"  [{entry['score']:.3f}]  {entry['memory']}")

# ---------------------------------------------------------------------------
# List all memories for a user
# ---------------------------------------------------------------------------

print("\n=== All memories for", USER_ID, "===")
all_memories = m.get_all(filters={"user_id": USER_ID})
for entry in all_memories["results"]:
    print(f"  {entry['id']}: {entry['memory']}")

# ---------------------------------------------------------------------------
# Update a memory
# ---------------------------------------------------------------------------

if all_memories["results"]:
    first_id = all_memories["results"][0]["id"]
    print(f"\n=== Updating memory {first_id} ===")
    m.update(first_id, "I love hiking and trail running in the mountains.")
    updated = m.get(first_id)
    print("Updated:", updated["memory"])

# ---------------------------------------------------------------------------
# Delete a memory
# ---------------------------------------------------------------------------

if all_memories["results"]:
    last_id = all_memories["results"][-1]["id"]
    print(f"\n=== Deleting memory {last_id} ===")
    m.delete(last_id)
    print("Deleted.")
