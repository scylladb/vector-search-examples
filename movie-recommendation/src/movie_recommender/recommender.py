from ..db.scylladb import ScyllaClient
from .embedding_creator import EmbeddingCreator
from .models import Movie
    
class MovieRecommender:
    
    def __init__(self):
        self.scylla_client = ScyllaClient()
        self.embedding_creator = EmbeddingCreator("all-MiniLM-L6-v2")
    
    def similar_movies(self, user_query: str, top_k=5) -> list[Movie]:
        user_query_embedding = self.embedding_creator.create_embedding(user_query)
        db_query = f"""SELECT *
                    FROM movies
                    ORDER BY plot_embedding ANN OF %s LIMIT %s;
                   """
        values = [user_query_embedding, top_k]
        results = self.scylla_client.query_data(db_query, values)
        return [Movie(**row) for row in results]

    def similar_movies_by_genre(self, user_query: str, genre: str, top_k=5) -> list[Movie]:
        user_query_embedding = self.embedding_creator.create_embedding(user_query)
        db_query = """SELECT *
                    FROM movies_by_genre
                    WHERE genre = %s
                    ORDER BY plot_embedding ANN OF %s LIMIT %s;
                   """
        values = [genre, user_query_embedding, top_k]
        results = self.scylla_client.query_data(db_query, values)
        return [Movie(**row) for row in results]
