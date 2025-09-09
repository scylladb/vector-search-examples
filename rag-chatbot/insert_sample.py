import json
from scylladb import ScyllaClient
import uuid

# TODO: improve insert performance by using `multiprocessing`
def insert_json_to_scylla(json_path, table_name):
    db_client = ScyllaClient()
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for row in data[:1000]:
        db_client.insert_data(
            table_name,
            {
                "chunk_id": uuid.UUID(row["chunk_id"]),
                "text": row["text"],
                "embedding": row["embedding"],
            }
        )

if __name__ == "__main__":
    print("Inserting sample data to ScyllaDB... (might take a few minutes)")
    insert_json_to_scylla("sample_vectors.json", "chunks")
    print("Done.")