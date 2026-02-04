from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path
from .movie_recommender.recommender import MovieRecommender
from .routers import movies


def lifespan_init():
    app.state.recommender = MovieRecommender()

def lifespan_shutdown():
    app.state.recommender.scylla_client.shutdown()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize resources on startup and cleanup on shutdown.
    """
    # Startup: Initialize the recommender once
    print("🚀 Initializing Movie Recommender...")
    lifespan_init()
    print("✅ Movie Recommender initialized")
    
    yield
    
    # Shutdown: Cleanup resources
    print("🔄 Shutting down...")
    if hasattr(app.state.recommender, 'scylla_client'):
        lifespan_shutdown()
    print("✅ Shutdown complete")


app = FastAPI(
    title="Movie Recommendation API",
    description="Vector search-powered movie recommendation system using ScyllaDB",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="movie_recc_static")



@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "movie-recommendation"}


# Include routers
app.include_router(movies.router, tags=["recommendations"])
