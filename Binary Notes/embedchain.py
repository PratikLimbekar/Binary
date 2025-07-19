from langchain_core.documents import Document
import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from chromadb.utils import embedding_functions

textsplitter = RecursiveCharacterTextSplitter(
    chunk_size=300, chunk_overlap=100, add_start_index = True
)


path = r"C:\Users\iprat\OneDrive\Desktop\AIPP\Binary Notes\chatlogs"
# print(path)
files = os.listdir(path)

textfiles = []

for file in files:
    if file.endswith(".txt"):
        textfiles.append(os.path.join(path, file))

documents = []
for file in textfiles:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
        documents.append(Document(page_content=content, metadata={"source": file}))

# print(textfiles)

# for i in txtfiles:
#     with open(i, 'r') as files:
#         text += i.read()


allsplits = textsplitter.split_documents(documents)

print(len(allsplits))

texts = [doc.page_content for doc in allsplits]
metadatas = [doc.metadata for doc in allsplits]
ids = [f"id_{i}" for i in range(len(allsplits))]


import chromadb
client = chromadb.Client()
embedding_fxn = embedding_functions.DefaultEmbeddingFunction()

collection = client.get_or_create_collection(name="Binary_Searches", embedding_function=embedding_fxn)

collection.add(
    documents=texts,
    metadatas=metadatas,
    ids=ids
)

results = collection.query(
    query_texts = ["Hawking Information Paradox"],
    n_results=1
)
print(results)
print("done")