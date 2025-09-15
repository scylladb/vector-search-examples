import os

# this gets overriden by environment variables (if you use them)
SCYLLADB_CONFIG = {
    "host": "node-0.aws-us-east-1.xxxxx.clusters.scylla.cloud",
    "port": "9042",
    "username": "scylla",
    "password": "xxxxxxxxx",
    "datacenter": "AWS_US_EAST_1",
    "keyspace": "semantic_cache"
}
OPENAI_API = {
    "apikey": os.environ.get("OPENAI_APIKEY", "xxxxxxxxxx"),
    "base_url": os.environ.get("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
}