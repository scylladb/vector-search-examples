import os

SCYLLADB_CONFIG = {
    "host": "node-0.aws-us-east-1.xxxxxxxx.clusters.scylla.cloud",
    "port": "9042",
    "username": "scylla",
    "password": "xxxxxxxxxxxxxx",
    "datacenter": "AWS_US_EAST_1",
    "keyspace": "recommend"
}

running_on_streamlit_cloud = bool(os.getenv("ON_STREAMLIT_CLOUD"))
if running_on_streamlit_cloud.lower() == "true":
    SCYLLADB_CONFIG = {
        "host": os.getenv("SCYLLADB_HOST"),
        "port": os.getenv("SCYLLADB_PORT"),
        "username": os.getenv("SCYLLADB_USERNAME"),
        "password": os.getenv("SCYLLADB_PASSWORD"),
        "datacenter": os.getenv("SCYLLADB_DATACENTER"),
        "keyspace": os.getenv("SCYLLADB_KEYSPACE")
    }