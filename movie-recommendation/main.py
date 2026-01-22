from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from movie_recommender.recommender import MovieRecommender
from routers import movies


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize resources on startup and cleanup on shutdown.
    """
    # Startup: Initialize the recommender once
    print("🚀 Initializing Movie Recommender...")
    app.state.recommender = MovieRecommender()
    print("✅ Movie Recommender initialized")
    
    yield
    
    # Shutdown: Cleanup resources
    print("🔄 Shutting down...")
    if hasattr(app.state.recommender, 'scylla_client'):
        app.state.recommender.scylla_client.shutdown()
    print("✅ Shutdown complete")


app = FastAPI(
    title="Movie Recommendation API",
    description="Vector search-powered movie recommendation system using ScyllaDB",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")



@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "movie-recommendation"}


# Include routers
app.include_router(movies.router, tags=["recommendations"])
