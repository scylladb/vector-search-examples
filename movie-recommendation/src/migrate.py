import os
from dotenv import load_dotenv
from db.scylladb import ScyllaClient

DEFAULT_KEYSPACE = "example_ks"

def read_schema(schema_path: str) -> str:
    """Read schema file and return content."""
    with open(schema_path, "r") as file:
        return file.read()

def parse_schema(schema_content: str, keyspace: str) -> list[str]:
    """Replace keyspace and split into executable statements."""
    if keyspace != DEFAULT_KEYSPACE:
        schema_content = schema_content.replace(DEFAULT_KEYSPACE, keyspace)
    return [stmt.strip() for stmt in schema_content.split(";") if stmt.strip()]

def execute_statements(session, statements: list[str]):
    """Execute schema statements with progress tracking."""
    total = len(statements)
    print(f"\nExecuting {total} statements...\n")
    
    for i, statement in enumerate(statements, 1):
        print(f"[{i}/{total}] {statement[:50]}...")
        session.execute(statement)
    
    print("✅ Migration completed!")

def main():
    
    keyspace = os.getenv("SCYLLADB_KEYSPACE", DEFAULT_KEYSPACE)
    schema_path = os.path.join(os.path.dirname(__file__), "db/schema.cql")
    
    print(f"Creating keyspace '{keyspace}' and tables...")
    
    client = ScyllaClient(migrate=True)
    session = client.get_session()
    
    schema_content = read_schema(schema_path)
    statements = parse_schema(schema_content, keyspace)
    execute_statements(session, statements)
    
    client.shutdown()

if __name__ == "__main__":
    load_dotenv()
    main()
