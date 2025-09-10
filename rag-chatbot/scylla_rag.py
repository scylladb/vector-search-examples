from typing import List
import uuid
from scylladb import ScyllaClient
from ollama import Client
from llama_index.core.node_parser import (
    SemanticDoubleMergingSplitterNodeParser,
    LanguageConfig,
)
from llama_index.core import SimpleDirectoryReader
from llama_index.core import Document
from llama_index.core.schema import BaseNode

class ScyllaRag():
    
    EMBEDDING_MODEL = "hf.co/CompendiumLabs/bge-base-en-v1.5-gguf"
    LANGUAGE_MODEL = "hf.co/bartowski/Llama-3.2-1B-Instruct-GGUF"
    
    def __init__(self):
        # Ollama running in Docker
        self.ollama_client = Client(host='http://ollama:11434')
        # Ollama running locally
        #self.ollama_client = Client()
        print("Downloading models from HuggingFace...")
        self.ollama_client.pull(self.EMBEDDING_MODEL)
        self.ollama_client.pull(self.LANGUAGE_MODEL)

    def create_embedding_ollama(self, content):
        return self.ollama_client.embed(model=self.EMBEDDING_MODEL, input=content)["embeddings"][0]
        
    def create_chunks(self, dir_path: str, files_limit=1) -> List[BaseNode]:
        """Create chunks from `.md` and `.rst` files in the defined directory.
        
        Uses LlamaIndex's `SemanticDoubleMergingSplitterNodeParser` to create chunks.

        Args:
            dir_path (str): The path to the directory containing documents.
            files_limit (int, optional): The maximum number of files to process. Defaults to 1.

        Returns:
            List[BaseNode]: A list of document chunks.
        """
        documents = SimpleDirectoryReader(input_dir=dir_path,
                                          recursive=True,
                                          num_files_limit=files_limit,
                                          required_exts=[".md", ".rst"],
                                          exclude_empty=True,
                                          exclude_hidden=True).load_data()
        # Filter out docs with no text
        documents = [doc for doc in documents if doc.text.strip()]
        
        splitter = SemanticDoubleMergingSplitterNodeParser(
            language_config=LanguageConfig(spacy_model="en_core_web_md"),
            initial_threshold=0.4, # merge sentences to create chunks
            appending_threshold=0.5, # merge chunk to the following sentence
            merging_threshold=0.5, # merge chunks to create bigger chunks
            max_chunk_size=2048,    
        )
        return splitter.get_nodes_from_documents(documents, show_progress=True)
    
    def vectorize(self, nodes: List[BaseNode], target_table: str) -> list[Document]:
        """Vectorize document chunks and store them in the specified ScyllaDB table.

        Args:
            nodes (List[BaseNode]): The document chunks to vectorize.
            target_table (str): The ScyllaDB table to store the chunks.

        Returns:
            list[Document]: A list of Document objects representing the vectorized chunks.
        """
        db_client = ScyllaClient()
        for node in nodes:
            chunk_id = uuid.uuid4()
            text = node.get_content()
            embedding = scylla_rag.create_embedding_ollama(text)
            db_client.insert_data(target_table, {"text": text,
                                                "chunk_id": chunk_id,
                                                "embedding": embedding})

    def fetch_chunks(self, table: str, user_query: str, top_k=5) -> List[Document]:
        db_client = ScyllaClient()
        user_query_embedding = self.create_embedding_ollama(user_query)
        db_query = f"""SELECT chunk_id, text
                    FROM {table} 
                    ORDER BY embedding ANN OF %s LIMIT %s;
                   """
        values = [user_query_embedding, top_k]
        return db_client.query_data(db_query, values)
    
    def query_llm_ollama(self, user_query: str, chunks: list[str]) -> str:
        """Query the LLM using Ollama."""
        context = ""
        for i, chunk in enumerate(chunks):
            context += f"\n\n Item {i+1}: {chunk}"
        system_prompt = f"""You are an AI assistant that answers user 
        questions by combining your reasoning ability with the information 
        provided below: \n
        {context}
        """
        stream = self.ollama_client.chat(
            model=self.LANGUAGE_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query},
            ],
            stream=True,
        )
        print("Chatbot response:")
        for chunk in stream:
            print(chunk["message"]["content"], end="", flush=True)
    
if __name__ == "__main__":
    scylla_rag = ScyllaRag()

    # ingest documents (only needs to run once)
    # nodes = scylla_rag.create_chunks("./scylladb/docs", files_limit=200)
    # scylla_rag.vectorize(nodes, target_table="rag.chunks")
    
    while True:
        user_input = input("\nEnter your question: ")
        nodes = scylla_rag.fetch_chunks("rag.chunks", user_input, top_k=3)
        
        chunks = [str(node['chunk_id']) for node in nodes]
        print("---\nRetrieved chunk IDs:", chunks)
        
        scylla_rag.query_llm_ollama(user_input, [node["text"] for node in nodes])
    