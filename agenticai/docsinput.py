import os
from langchain.text_splitter import CharacterTextSplitter
from langchain.schema import Document
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from ragtoai import ragbasedresponse

# Global variables so main.py can reuse them
embedding_function = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(
    name="binary_docs",
    embedding_function=embedding_function
)

# Step 1: Load documents from directory
def load_text_files(directory):
    documents = []
    for dirpath, _, filename in os.walk(directory):
        if filename.endswith('.txt'):
            file_path = os.path.join(dirpath, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    text = file.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='latin-1') as file:
                    text = file.read()
            documents.append(Document(page_content=text, metadata={"source": filename}))
            print(f"[LOADED] {filename}")
    return documents

# Step 2-5: Full pipeline to load, split, embed and insert
def load_directory_and_embed(directory):
    documents = load_text_files(directory)
    if not documents:
        print("No documents to load.")
        return

    # Step 2: Split into chunks
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=4)
    docs = text_splitter.split_documents(documents)

    # Step 3: Prepare and add to Chroma
    texts = [doc.page_content for doc in docs]
    metadatas = [doc.metadata for doc in docs]
    ids = [f"{doc.metadata['source']}_chunk_{i}" for i, doc in enumerate(docs)]


    if texts and metadatas and ids:
        existing_ids = set(collection.get()["ids"])
        new_texts, new_metadatas, new_ids = [], [], []

        for i, id_ in enumerate(ids):
            if id_ not in existing_ids:
                new_texts.append(texts[i])
                new_metadatas.append(metadatas[i])
                new_ids.append(id_)

        if new_texts:
            collection.add(
                documents=new_texts,
                metadatas=new_metadatas,
                ids=new_ids
            )
            print(f"[EMBEDDED] {len(new_texts)} new chunks added.")
        else:
            print("[SKIPPED] No new chunks to embed.")
    else:
        print("Nothing to add. Check your input documents.")
