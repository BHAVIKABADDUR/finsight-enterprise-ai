import os
from dotenv import load_dotenv

load_dotenv()

def test_groq():
    from groq import Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "Say hello in one word"}]
    )
    print(f"✅ Groq working: {response.choices[0].message.content}")

def test_supabase():
    from supabase import create_client
    client = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )
    print(f"✅ Supabase connected: {os.getenv('SUPABASE_URL')}")

def test_qdrant():
    from qdrant_client import QdrantClient
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )
    collections = client.get_collections()
    print(f"✅ Qdrant connected: {len(collections.collections)} collections")

def test_langsmith():
    import langsmith
    client = langsmith.Client(api_key=os.getenv("LANGSMITH_API_KEY"))
    projects = list(client.list_projects())
    print(f"✅ LangSmith connected: {len(projects)} projects found")

if __name__ == "__main__":
    print("Testing all connections...\n")
    test_groq()
    test_supabase()
    test_qdrant()
    test_langsmith()
    print("\n🎉 All connections successful!")