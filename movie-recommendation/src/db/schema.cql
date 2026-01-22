CREATE KEYSPACE IF NOT EXISTS example_ks WITH replication = {'class': 'NetworkTopologyStrategy', 'replication_factor': '3'}
AND TABLETS = {'enabled': 'true'};

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
) WITH cdc = {'enabled': 'true'};


CREATE INDEX IF NOT EXISTS ann_index ON example_ks.movies(plot_embedding) 
USING 'vector_index'
WITH OPTIONS = { 'similarity_function': 'DOT_PRODUCT' };
