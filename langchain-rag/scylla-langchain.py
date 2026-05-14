"""
ScyllaDB + LangChain demo: RAG + persistent chat memory in one cluster.

Prerequisites:
    pip install langchain langchain-community langchain-openai langchain-groq \
                langchain-text-splitters cassio scylla-driver python-dotenv

Copy demo/.env.example to demo/.env and fill in your credentials.
"""

import os
from dotenv import load_dotenv

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.policies import DCAwareRoundRobinPolicy
import cassio

from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Cassandra
from langchain_community.chat_message_histories import CassandraChatMessageHistory
from langchain_classic.memory import ConversationBufferMemory
from langchain_groq import ChatGroq
from langchain_classic.chains import ConversationalRetrievalChain

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

CONTACT_POINTS = os.environ["SCYLLADB_CONTACT_POINTS"].split(",")
DATACENTER = os.environ["SCYLLADB_DATACENTER"]
USERNAME = os.environ["SCYLLADB_USERNAME"]
PASSWORD = os.environ["SCYLLADB_PASSWORD"]
KEYSPACE = os.environ["SCYLLADB_KEYSPACE"]

# URLs of tech articles to load into the vector store
ARTICLE_URLS = [
    "https://docs.scylladb.com/stable/get-started/scylladb-basics.html",
    "https://docs.scylladb.com/stable/get-started/data-modeling/query-design.html",
]

SESSION_ID = "demo-session-1"

# ---------------------------------------------------------------------------
# 1. Connect to ScyllaDB Cloud
# ---------------------------------------------------------------------------

print("Connecting to ScyllaDB Cloud...")
cluster = Cluster(
    contact_points=CONTACT_POINTS,
    auth_provider=PlainTextAuthProvider(USERNAME, PASSWORD),
    load_balancing_policy=DCAwareRoundRobinPolicy(local_dc=DATACENTER),
)
session = cluster.connect()

# Create the keyspace if it doesn't exist
session.execute(
    f"""
    CREATE KEYSPACE IF NOT EXISTS {KEYSPACE}
    WITH replication = {{'class': 'NetworkTopologyStrategy', '{DATACENTER}': 3}}
    """
)

cassio.init(session=session, keyspace=KEYSPACE)
print(f"Connected. Keyspace: {KEYSPACE}")

# ---------------------------------------------------------------------------
# 2. Build the vector store (RAG)
# ---------------------------------------------------------------------------

print("\nLoading articles and building vector store...")
loader = WebBaseLoader(ARTICLE_URLS)
docs = loader.load()

chunks = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
).split_documents(docs)
print(f"  {len(docs)} articles → {len(chunks)} chunks")

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = Cassandra(
    embedding=embeddings,
    table_name="rag_docs",
)
vectorstore.add_documents(chunks)
retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
print("  Vector store ready (table: rag_docs)")

# Quick sanity check
sample = vectorstore.similarity_search("What is a vector database?", k=2)
print(f"\nSanity check — top 2 results for 'What is a vector database?':")
for i, doc in enumerate(sample, 1):
    print(f"  [{i}] {doc.page_content[:120].strip()}...")

# ---------------------------------------------------------------------------
# 3. Set up persistent chat memory
# ---------------------------------------------------------------------------

print(f"\nSetting up chat memory (session_id={SESSION_ID!r})...")
chat_history = CassandraChatMessageHistory(
    session_id=SESSION_ID,
    table_name="chat_history",
)
memory = ConversationBufferMemory(
    chat_memory=chat_history,
    return_messages=True,
    memory_key="chat_history",
    output_key="answer",
)

existing = chat_history.messages
if existing:
    print(f"  Loaded {len(existing)} messages from a previous session.")
else:
    print("  No prior history found — starting a fresh conversation.")

# ---------------------------------------------------------------------------
# 4. Wire everything into a ConversationalRetrievalChain
# ---------------------------------------------------------------------------

llm = ChatGroq(model="llama-3.3-70b-versatile")

chain = ConversationalRetrievalChain.from_llm(
    llm=llm,
    retriever=retriever,
    memory=memory,
    return_source_documents=False,
)

# ---------------------------------------------------------------------------
# 5. Run a two-turn conversation
# ---------------------------------------------------------------------------

questions = [
    "What is a vector database and why is it useful for AI applications?",
    "How does RAG work with the vector database you just described?",
]

print("\n" + "=" * 60)
for q in questions:
    print(f"\nUser: {q}")
    result = chain.invoke({"question": q})
    print(f"Assistant: {result['answer']}")

print("\n" + "=" * 60)
print(
    "\nConversation persisted to ScyllaDB. "
    "Re-run this script with the same SESSION_ID to continue it."
)
print(f"  Tables in keyspace {KEYSPACE!r}: rag_docs, chat_history")

cluster.shutdown()
