#use uvicorn server:app --reload to start the server
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class InputData(BaseModel):
    input: str

class JSONInputData(BaseModel):
    data: str

@app.get("/favicon.ico")
async def favicon():
    return {}

@app.get("/")
async def root():
    return {"message": "Hello, World!"}

@app.post('/ai-response')
async def ai_response(data: InputData):
    from gemini import getairesponsefornotes
    ai_response = getairesponsefornotes(data.input)
    return {"response": ai_response}

@app.post('/ragdb/store')
async def store_in_ragdb(data: JSONInputData):
    from ragmodel import addJSONtoRAGdb
    addJSONtoRAGdb(data.data)
    return {"message": "Data added to RAG database successfully."}

