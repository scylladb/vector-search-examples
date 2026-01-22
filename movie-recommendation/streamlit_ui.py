import streamlit as st
from src.movie_recommender.recommender import MovieRecommender
from src.movie_recommender.models import Movie

recommender = MovieRecommender()

st.set_page_config(
    page_title="Movie Recommender",
    page_icon="🎬",
    layout="centered",
)

# Header
st.title("🎬 Movie recommendation")
st.subheader("ScyllaDB Vector Search DEMO")
st.markdown("Source code: https://github.com/scylladb/vector-search-examples/tree/main/movie-recommendation")

# Input area
with st.form("search_form", clear_on_submit=False):
    col1, col2 = st.columns([3, 1])
    with col1:
        user_query = st.text_input("What kind of movie are you looking for?",placeholder="e.g. time travelling")
    with col2:
        top_k = st.number_input("Number of recommendations", min_value=3, max_value=15, value=4, step=1)

    search_button = st.form_submit_button("Get Recommendations", width="stretch")

def show_poster(poster: str) -> str:
    if poster:
        base_url = "https://image.tmdb.org/t/p/original"
        url = f"{base_url}{poster}"
        st.image(url, width=200)
    else:
        st.caption("Poster not found")

def display_best_match(best_match: Movie):
    movie_poster = best_match.poster_url
    col1, col2 = st.columns([1, 2])
    with col1:
        show_poster(movie_poster)
    with col2:
        st.markdown(f"### {best_match.title}")
        st.write(best_match.plot[:500] + "...")
        
def display_more_recommendations(movies: list[Movie]):
    cols = st.columns(3)
    for i, movie in enumerate(movies):
        with cols[i % 3]:
            poster = movie.poster_url
            show_poster(poster)
            st.write(movie.title)


def display_search_results():
    with st.spinner("🔍 Searching for recommendations..."):
        movies = recommender.similar_movies(user_query, top_k)
        if movies:
            st.subheader("⭐ Best Match")
            best_match = movies[0]
            display_best_match(best_match)
            st.divider()
                
            st.subheader("🎥 More Recommendations")
            rest_of_the_movies = movies[1:]
            display_more_recommendations(rest_of_the_movies)
        else:
            st.error("❌ No similar movies found.")

if search_button:
    if not user_query or not user_query.strip():
        st.warning("⚠️ Please enter some text to get recommendations.")
    else:
        try:
            display_search_results()
        except Exception as e:
            st.error(f"⚠️ Error: {str(e)}")
