"""
Schema migration script for the mem0 ScyllaDB example.

Reads credentials from .env (same file used by main.py) and applies
schema.cql to the cluster — no cqlsh required.

Usage:
  uv run migrate.py
"""

import os
import pathlib
from dotenv import load_dotenv
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.policies import DCAwareRoundRobinPolicy

# ---------------------------------------------------------------------------
# Load environment
# ---------------------------------------------------------------------------

load_dotenv()

SCYLLADB_ADDRESS    = os.environ["SCYLLADB_ADDRESS"]
SCYLLADB_USERNAME   = os.environ["SCYLLADB_USERNAME"]
SCYLLADB_PASSWORD   = os.environ["SCYLLADB_PASSWORD"]
SCYLLADB_DATACENTER = os.environ.get("SCYLLADB_DATACENTER", "AWS_US_EAST_1")

# ---------------------------------------------------------------------------
# Connect
# ---------------------------------------------------------------------------

cluster = Cluster(
    contact_points=[SCYLLADB_ADDRESS],
    port=9042,
    auth_provider=PlainTextAuthProvider(
        username=SCYLLADB_USERNAME,
        password=SCYLLADB_PASSWORD,
    ),
    load_balancing_policy=DCAwareRoundRobinPolicy(local_dc=SCYLLADB_DATACENTER),
    protocol_version=4,
)

session = cluster.connect()

# ---------------------------------------------------------------------------
# Execute schema.cql — split on ";" and skip blank / comment-only blocks
# ---------------------------------------------------------------------------

schema_path = pathlib.Path(__file__).parent / "schema.cql"
raw = schema_path.read_text()

statements = [s.strip() for s in raw.split(";") if s.strip()]

for stmt in statements:
    # Skip comment-only blocks
    lines = [l for l in stmt.splitlines() if not l.strip().startswith("--")]
    cql = "\n".join(lines).strip()
    if not cql:
        continue
    print(f"Executing: {cql[:80]}{'...' if len(cql) > 80 else ''}")
    session.execute(cql)

print("\nSchema applied successfully.")
cluster.shutdown()
