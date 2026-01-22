import os
from dotenv import load_dotenv
load_dotenv()
# extra configuration if needed

SCYLLADB_KEYSPACE = os.getenv("SCYLLADB_KEYSPACE", "example_ks")