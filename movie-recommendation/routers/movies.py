from fastapi import APIRouter, HTTPException, Request
from schemas import RecommendRequest, RecommendResponse, MovieResponse
from movie_recommender.models import Movie

router = APIRouter()


@router.post("/recommend", response_model=RecommendResponse)
async def recommend_movies(request: Request, body: RecommendRequest):
    """
    Get movie recommendations based on a text query.
    
    The endpoint performs vector similarity search on movie plots to find
    the most relevant movies matching the user's query.
    """
    try:
        recommender = request.app.state.recommender
        
        # Get recommendations from the business logic
        movies = recommender.similar_movies(body.query, body.top_k)
        
        # Convert Movie dataclasses to Pydantic models (exclude embedding)
        movie_responses = [
            MovieResponse(
                id=movie.id,
                title=movie.title,
                release_date=movie.release_date,
                tagline=movie.tagline,
                genre=movie.genre,
                poster_url=movie.poster_url,
                imdb_id=movie.imdb_id,
                plot=movie.plot
            )
            for movie in movies
        ]
        
        return RecommendResponse(movies=movie_responses, count=len(movie_responses))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting recommendations: {str(e)}")
