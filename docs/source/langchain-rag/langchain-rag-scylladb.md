# RAG with LangChain and ScyllaDB

This tutorial shows you how to build a **RAG chatbot with persistent chat memory** using [ScyllaDB Vector Search](https://www.scylladb.com/product/vector-search/) and [LangChain](https://python.langchain.com/).

## What you'll build

A conversational RAG chatbot that:
- Loads ScyllaDB documentation pages and stores them as vector embeddings in ScyllaDB
- Retrieves the most relevant chunks via ANN (approximate nearest-neighbor) search on every turn
- Keeps a full conversation history in ScyllaDB so the session survives restarts
- Uses Groq (Llama 3.3 70B) as the LLM

Both the **vector store** (`rag_docs`) and the **chat history** (`chat_history`) live in the same ScyllaDB keyspace — no extra infrastructure needed.

## How it works

```
User question
      │
      ▼
ConversationalRetrievalChain (LangChain)
      │
      ├─► Retriever — ANN search on rag_docs
      │         └─► ScyllaDB vector_index (cosine similarity)
      │
      ├─► Chat history — CassandraChatMessageHistory → chat_history table
      │
      └─► LLM (Groq / Llama 3.3 70B)
                └─► Answer
```

## Prerequisites

- [ScyllaDB Cloud](https://cloud.scylladb.com/) cluster with Vector Search enabled
- [Groq API key](https://console.groq.com/) (free tier is sufficient)
- [Python 3.10 or newer](https://www.python.org/downloads/) installed
- [Git](https://git-scm.com/downloads) installed

## Clone the repository

```bash
git clone https://github.com/scylladb/vector-search-examples.git
cd vector-search-examples/langchain-rag
```

## Install dependencies

With `uv` (recommended):

```bash
uv pip install langchain langchain-community langchain-classic langchain-huggingface \
               langchain-groq langchain-text-splitters cassio scylla-driver python-dotenv
```

Or with `pip`:

```bash
pip install langchain langchain-community langchain-classic langchain-huggingface \
            langchain-groq langchain-text-splitters cassio scylla-driver python-dotenv
```

## Configure credentials

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Open `.env` and set the following variables:

| Variable | Description |
|---|---|
| `SCYLLADB_CONTACT_POINTS` | Comma-separated list of node hostnames |
| `SCYLLADB_DATACENTER` | Local datacenter name (e.g. `AWS_US_EAST_1`) |
| `SCYLLADB_USERNAME` | ScyllaDB username |
| `SCYLLADB_PASSWORD` | ScyllaDB password |
| `SCYLLADB_KEYSPACE` | Keyspace to use (created automatically if it doesn't exist) |
| `GROQ_API_KEY` | Your Groq API key |

Find your ScyllaDB Cloud credentials in the [ScyllaDB Cloud console](https://cloud.scylladb.com/) under your cluster's **Connect** tab.

## Run the demo

```bash
python scylla-langchain.py
```

The script will:
1. Connect to ScyllaDB and create the keyspace, `rag_docs` table, and vector index
2. Load two ScyllaDB documentation pages and embed them into the vector store
3. Run a two-turn conversation, printing both questions and answers
4. Persist the conversation history to ScyllaDB

Re-run the script with the same `SESSION_ID` (default: `demo-session-1`) to continue the conversation from where it left off.

## Schema overview

`cassio` automatically creates both tables when the script first runs:

```cql
-- Vector store: stores document chunks + embeddings
CREATE TABLE IF NOT EXISTS <keyspace>.rag_docs (
    row_id     text PRIMARY KEY,
    body_blob  text,
    metadata_s map<text, text>,
    vector     vector<float, 384>
);

CREATE CUSTOM INDEX IF NOT EXISTS rag_docs_ann
ON <keyspace>.rag_docs (vector)
USING 'StorageAttachedIndex'
WITH OPTIONS = {'similarity_function': 'cosine'};

-- Chat history: persists conversation turns
CREATE TABLE <keyspace>.chat_history (
    partition_id text,
    row_id       timeuuid,
    body_blob    text,
    PRIMARY KEY (partition_id, row_id)
) WITH CLUSTERING ORDER BY (row_id ASC);
```
