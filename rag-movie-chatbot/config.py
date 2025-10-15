import os

SCYLLADB_CONFIG = {
    "host": "node-0.aws-us-east-1.xxxxxxxxx.clusters.scylla.cloud",
    "port": "9042",
    "username": "scylla",
    "password": "xxxxxxxxx",
    "datacenter": "AWS_US_EAST_1",
    "keyspace": "recommend"
}

GROQ_API_KEY = "xxxxxxxxxxx"

running_on_streamlit_cloud = os.getenv("ON_STREAMLIT_CLOUD")
if running_on_streamlit_cloud and running_on_streamlit_cloud.lower() == "true":
    SCYLLADB_CONFIG = {
        "host": os.getenv("SCYLLADB_HOST"),
        "port": os.getenv("SCYLLADB_PORT"),
        "username": os.getenv("SCYLLADB_USERNAME"),
        "password": os.getenv("SCYLLADB_PASSWORD"),
        "datacenter": os.getenv("SCYLLADB_DATACENTER"),
        "keyspace": os.getenv("SCYLLADB_KEYSPACE")
    }
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")