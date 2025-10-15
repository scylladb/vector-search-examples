import streamlit as st
from llm_provider import LLMProvider
from movie_rag import MovieRAG

st.title("Every story is a database story.")
st.subheader("Provide a movie plot and I'll turn it into a database story:)")


llm_context_prompt = """
Rewrite the following movie plot as if it were a story 
about a low-latency database named ScyllaDB. 
Treat ScyllaDB as the protagonist — a fast, high-performant database
system designed to handle massive workloads. Keep the spirit and structure of
the movie, but make it fit the database world.
Don't mention any other specific databases by name. 
Response should 50 words or less. The plot: {plot}"""

def show_poster(poster: str) -> str:
    if poster:
        base_url = "https://image.tmdb.org/t/p/original"
        url = f"{base_url}{poster}"
        st.image(url, width=200)
    else:
        st.caption("Poster not found")

def get_all_messages():
    return [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]

def process_movie_plot(plot_text):
    """Process a movie plot and generate response"""
    st.session_state.messages.append({"role": "user", "content": plot_text})
    with st.chat_message("user"):
        st.markdown(plot_text)

    with st.chat_message("assistant", avatar=st.session_state.scylla_icon_img):
        messages = get_all_messages()
        rag_results = st.session_state.movie_rag.similar_movies(plot_text, top_k=1)
        rag_movie_plot = rag_results[0].plot
        
        context_prompt = llm_context_prompt.format(plot=rag_movie_plot)
        messages.append({"role": "system", "content": context_prompt})
        response = st.session_state.llm_provider.generate_response(messages)
        stream_response = st.write_stream(response)
        st.markdown(f"**Referenced movie:** `{rag_results[0].title}`", )
        show_poster(rag_results[0].poster_url)
    
    st.session_state.messages.append({"role": "assistant", "content": stream_response})


if "scylla_icon_img" not in st.session_state:
    st.session_state.scylla_icon_img = "https://sphinx-theme.scylladb.com/_static/img/mascots-2/forward.svg"

if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "llm_provider" not in st.session_state:
    st.session_state.llm_provider = LLMProvider()
    
if "movie_rag" not in st.session_state:
    st.session_state.movie_rag = MovieRAG()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_movie_plot := st.chat_input("Enter a random movie plot. E.g: Rebels flee, Vader reveals shocking truth"):
    process_movie_plot(user_movie_plot)

example_plots = [
    "Harry Potter defeats Voldemort",
    "Marty McFly meets his parents in the past.",
    "Thanos collects all Infinity Stones"]

col1, col2, col3 = st.columns(3)

chosen_plot = None
with col1:
    if st.button(example_plots[0], use_container_width=True):
        chosen_plot = example_plots[0]
with col2:
    if st.button(example_plots[1], use_container_width=True):
        chosen_plot = example_plots[1]
with col3:
    if st.button(example_plots[2], use_container_width=True):
        chosen_plot = example_plots[2]
if chosen_plot:
    process_movie_plot(chosen_plot)