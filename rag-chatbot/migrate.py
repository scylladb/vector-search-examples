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