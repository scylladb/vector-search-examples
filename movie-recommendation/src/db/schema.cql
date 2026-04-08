CREATE KEYSPACE IF NOT EXISTS example_ks WITH replication = {'class': 'NetworkTopologyStrategy', 'replication_factor': '3'};

CREATE TABLE IF NOT EXISTS example_ks.movies (
    id INT,
    release_date TIMESTAMP,
    title TEXT,
    tagline TEXT,
    genre TEXT,
    imdb_id TEXT,
    poster_url TEXT,
    plot TEXT,
    plot_embedding VECTOR<FLOAT, 384>,
    PRIMARY KEY (id)
);


CREATE INDEX IF NOT EXISTS ann_index ON example_ks.movies(plot_embedding)
USING 'vector_index'
WITH OPTIONS = { 'similarity_function': 'DOT_PRODUCT' };

CREATE TABLE IF NOT EXISTS example_ks.movies_by_genre (
    genre TEXT,
    id INT,
    release_date TIMESTAMP,
    title TEXT,
    tagline TEXT,
    imdb_id TEXT,
    poster_url TEXT,
    plot TEXT,
    plot_embedding VECTOR<FLOAT, 384>,
    PRIMARY KEY (genre, id)
);

CREATE CUSTOM INDEX IF NOT EXISTS ann_index_by_genre
ON example_ks.movies_by_genre((genre), plot_embedding)
USING 'vector_index'
WITH OPTIONS = { 'similarity_function': 'DOT_PRODUCT' };
