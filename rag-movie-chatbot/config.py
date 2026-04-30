import os
from dotenv import load_dotenv

load_dotenv()

SCYLLADB_CONFIG = {
    "host": os.getenv("SCYLLADB_HOST"),
    "port": os.getenv("SCYLLADB_PORT", "9042"),
    "username": os.getenv("SCYLLADB_USERNAME", "scylla"),
    "password": os.getenv("SCYLLADB_PASSWORD"),
    "datacenter": os.getenv("SCYLLADB_DATACENTER"),
    "keyspace": os.getenv("SCYLLADB_KEYSPACE", "recommend")
}

GROQ_API_KEY = os.getenv("GROQ_API_KEY")