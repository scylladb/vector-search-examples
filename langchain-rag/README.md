# ScyllaDB + LangChain RAG Demo

A minimal example showing how to build a **RAG chatbot with persistent chat memory** using ScyllaDB Cloud and LangChain — all in a single cluster.

The script:
1. Connects to ScyllaDB Cloud and creates the keyspace and tables
2. Loads ScyllaDB documentation pages and stores them as embeddings in a vector store (`rag_docs`)
3. Sets up a persistent conversation history backed by ScyllaDB (`chat_history`)
4. Wires everything into a LangChain `ConversationalRetrievalChain` powered by Groq (Llama 3.3 70B)
5. Runs a two-turn demo conversation and persists the history so it survives restarts

## Prerequisites

- [ScyllaDB Cloud](https://cloud.scylladb.com/) cluster with Vector Search enabled
- [Groq API key](https://console.groq.com/) (free tier works)
- Python 3.10+

## Setup

**1. Install dependencies**

```bash
pip install langchain langchain-community langchain-classic langchain-huggingface \
            langchain-groq langchain-text-splitters cassio scylla-driver python-dotenv
```

Or with `uv`:

```bash
uv pip install langchain langchain-community langchain-classic langchain-huggingface \
               langchain-groq langchain-text-splitters cassio scylla-driver python-dotenv
```

**2. Configure credentials**

```bash
cp .env.example .env
```

Edit `.env` and fill in your ScyllaDB Cloud connection details and Groq API key:

| Variable | Description |
|---|---|
| `SCYLLADB_CONTACT_POINTS` | Comma-separated list of node hostnames |
| `SCYLLADB_DATACENTER` | Local datacenter name (e.g. `AWS_US_EAST_1`) |
| `SCYLLADB_USERNAME` | ScyllaDB username |
| `SCYLLADB_PASSWORD` | ScyllaDB password |
| `SCYLLADB_KEYSPACE` | Keyspace to use (will be created if it doesn't exist) |
| `GROQ_API_KEY` | Your Groq API key |

**3. Run the demo**

```bash
python scylla-langchain.py
```

Re-running the script with the same `SESSION_ID` will reload the previous conversation from ScyllaDB and continue from where you left off.

## How it works

```
User question
      │
      ▼
ConversationalRetrievalChain
      │
      ├─► Retriever (ANN vector search on rag_docs)
      │         └─► ScyllaDB vector_index (cosine similarity)
      │
      ├─► Chat history (CassandraChatMessageHistory → chat_history table)
      │
      └─► LLM (Groq / Llama 3.3 70B)
                └─► Answer
```

Both the vector store and the chat history live in the same ScyllaDB keyspace, so there is no extra infrastructure to manage.
