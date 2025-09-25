from langchain_community.document_loaders import TextLoader, JSONLoader
import flatdict
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb
import json

model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

chroma_client = chromadb.PersistentClient(path= "./chroma_db")

def addJSONtoRAGdb(data):
    """
    Adds the given dictionary to the RAG database.
    """
    collection = chroma_client.get_or_create_collection("Binary_RAG_DB")

    text = json.dumps(data)
    print("Added to text:", text)
    textsplitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    allsplits = textsplitter.split_text(text)
    print("All splits:", allsplits)
    ids = [str(collection.count() + i + 1) for i in range(1, len(allsplits) + 1)]
    embeddings = model.encode(allsplits).tolist() # Convert embeddings (numpy Array) to list for ChromaDB compatibility

    
    collection.add(
            documents=allsplits,
            ids=ids,
            embeddings=embeddings
        )

    print("Added to collection: ", collection.count())

