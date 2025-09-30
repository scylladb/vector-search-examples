import csv
from datetime import datetime
from db.scylladb import ScyllaClient
from embedding_creator import EmbeddingCreator

class MovieLoader:
    def __init__(self):
        self.scylla_client = ScyllaClient()
        self.embedding_creator = EmbeddingCreator("all-MiniLM-L6-v2")

    def create_embedding(self, text: str) -> list[float]:
        return self.embedding_creator.create_embedding(text)

    def ingest_csv(self, csv_file, table_name):
        with ScyllaClient() as client:
            with open(csv_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data = {
                        "id": int(row["id"]),
                        "release_date": datetime.strptime(row["release_date"], "%Y-%m-%d"),
                        "title": row["title"],
                        "tagline": row["tagline"],
                        "genre": row["genres"],
                        "poster_url": row["poster_path"],
                        "imdb_id": row["imdb_id"],
                        "plot": row["overview"],
                        "plot_embedding": self.create_embedding(row["overview"]),
                    }
                    client.insert_data(table_name, data)


if __name__ == "__main__":
    CSV_FILE = "data/movies_sample.csv"
    loader = MovieLoader()
    print("⏳ Ingestion started...")
    loader.ingest_csv(CSV_FILE, "recommend.movies")
    print(f"✅ Finished ingesting {CSV_FILE}")
