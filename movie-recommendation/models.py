from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class Movie(BaseModel):
    id: int
    title: Optional[str] = None
    release_date: Optional[datetime] = None
    tagline: Optional[str] = None
    genre: Optional[str] = None
    poster_url: Optional[str] = None
    imdb_id: Optional[str] = None
    plot: Optional[str] = None
    plot_embedding: Optional[list[float]] = None