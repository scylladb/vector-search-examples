from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class RecommendRequest(BaseModel):
    query: str = Field(..., description="Search query to find similar movies")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of recommendations to return")
    genre: Optional[str] = Field(default=None, description="Optional genre filter for scoped vector search")


class MovieResponse(BaseModel):
    id: int
    title: Optional[str] = None
    release_date: Optional[datetime] = None
    tagline: Optional[str] = None
    genre: Optional[str] = None
    poster_url: Optional[str] = None
    imdb_id: Optional[str] = None
    plot: Optional[str] = None


class RecommendResponse(BaseModel):
    movies: list[MovieResponse]
    count: int
