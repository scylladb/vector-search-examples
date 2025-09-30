from db.scylladb import ScyllaClient
from embedding_creator import EmbeddingCreator
from models import Movie
    
class MovieRecommender:
    
    def __init__(self):
        self.scylla_client = ScyllaClient()
        self.embedding_creator = EmbeddingCreator("all-MiniLM-L6-v2")
    
    def similar_movies(self, user_query: str, top_k=5) -> list[Movie]:
        db_client = ScyllaClient()
        user_query_embedding = self.embedding_creator.create_embedding(user_query)
        db_query = f"""SELECT *
                    FROM recommend.movies
                    ORDER BY plot_embedding ANN OF %s LIMIT %s;
                   """
        values = [user_query_embedding, top_k]
        results = db_client.query_data(db_query, values)
        return [Movie(**row) for row in results]
    
if __name__ == "__main__":
    recommender = MovieRecommender()
    user_query = "Time travelling"
    print(f"User query: {user_query}")
    
    movies = recommender.similar_movies("recommend.movies", user_query, top_k=5)
    movie_plots = "\n\n".join([movie["plot"] for movie in movies])
    movie_titles = "\n".join([f'{movie["title"]} (id: {movie["id"]})' for movie in movies])
    
    print(f"\nRetrieved movies:\n{movie_titles}\n")