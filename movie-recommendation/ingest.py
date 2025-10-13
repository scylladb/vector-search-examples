import csv
from datetime import datetime
from db.scylla_loader import ScyllaLoader
from config import SCYLLADB_CONFIG
import os
import ast

os.environ["TOKENIZERS_PARALLELISM"] = "false"

class MovieLoader:
    
    DATE_FORMAT = "%Y-%m-%d"
    
    def _ingest(self, data: list[dict]):
        loader = ScyllaLoader()
        loader.ingest_data(
            data=data,
            address=SCYLLADB_CONFIG["host"],
            keyspace=SCYLLADB_CONFIG["keyspace"],
            dc=SCYLLADB_CONFIG["datacenter"],
            table="movies",
        )

    def _date_is_valid(self, date_str: str) -> bool:
        if date_str == "":
            return False
        try:
            datetime.strptime(date_str, self.DATE_FORMAT)
        except ValueError:
            return False
        return True
    
    def string_to_float_list(self, s: str) -> list[float]:
        """Convert string to embedding. String should be in the format of `"[0.1, 0.2, 0.3]"` 
        """
        try:
            return ast.literal_eval(s)
        except (SyntaxError) as e:
            raise SyntaxError(f"Error parsing plot_embedding: {e}")
    
    def string_to_date(self, s: str) -> datetime:
        """Convert string to datetime object."""
        try:
            return datetime.strptime(s, self.DATE_FORMAT)
        except ValueError as e:
            raise ValueError(f"Error parsing release_date: {e}")
    
    def row_is_valid(self, row: dict) -> bool:
        """Check if a row has valid data. Include checks for:
        
        - date is the correct format
        - plot_embedding is not empty
        """
        date = row["release_date"].strip()
        return self._date_is_valid(date) and \
               row["plot_embedding"].strip() != ""

    def _prepare_csv(self, csv_file: str) -> list[dict]:
        rows = []
        with open(csv_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not self.row_is_valid(row): # skip row if it's not valud
                    continue
                plot_embedding = self.string_to_float_list(row["plot_embedding"])
                data = {
                    "id": int(row["id"]),
                    "release_date": self.string_to_date(row["release_date"]),
                    "title": row["title"],
                    "tagline": row["tagline"],
                    "genre": row["genres"],
                    "poster_url": row["poster_path"],
                    "imdb_id": row["imdb_id"],
                    "plot": row["overview"],
                    "plot_embedding": plot_embedding,
                }
                rows.append(data)
        return rows

    def start_loader(self, csv_file: str):
        data = self._prepare_csv(csv_file)
        self._ingest(data)


if __name__ == "__main__":
    loader = MovieLoader()
    print("⏳ Ingestion started...")
    data_folder = "data/"
    files = [data_folder + f for f in os.listdir(data_folder) if f.endswith(".csv")]
    total_file_count = len(files)
    counter = 0
    for csv_file in files:
        counter += 1
        print(f"📄 Ingesting sample data {counter}/{total_file_count} ...")
        loader.start_loader(csv_file)
    
