from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from ..schemas import RecommendRequest, RecommendResponse, MovieResponse
import logging
import json

# Configure logging
#logging.basicConfig(level=logging.INFO)

router = APIRouter()
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


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
    
@router.get("/start-sse", response_class=HTMLResponse)
async def start_bot_message(request: Request, query, top_k):
    context = {"request": request,
               "query_string": request.url.query,
               "query": query,
               "top_k": top_k}
    return templates.TemplateResponse("partials/bot_message.html", context)


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main chat HTML page."""
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/generate-story/stream")
async def generate_story_stream(request: Request, query: str, top_k: int):
    """Turn any movie plot into a Scylla story"""
    
    try:
        logging.info(f"Received query: '{query}' with top_k: {top_k}")
        
        recommender = request.app.state.recommender
        
        # Get movie recommendations from the business logic
        movies = recommender.similar_movies(query, top_k)
        logging.info(f"Found {len(movies)} movies, first movie: {movies[0].title if movies else 'None'}")
        
        movie = movies[0]
        
        def stream_generator():
            # Send movie data first
            movie_data = {
                "title": movie.title,
                "poster_url": movie.poster_url,
                "plot": movie.plot
            }
            yield f"event: movie_data\ndata: {json.dumps(movie_data)}\n\n"
            
            # Stream plot character by character
            for char in movie.plot:
                yield f"event: content\ndata: {char}\n\n"
            
            # Send done event
            yield f"event: done\ndata: {json.dumps({'status': 'complete'})}\n\n"
        
        return StreamingResponse(
            stream_generator(), 
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
