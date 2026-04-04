from fastapi import FastAPI
from services import search_papers

app = FastAPI()

@app.get("/")
def home():
    return {"test": "Working"}

# @app.get("/search")
# async def search(query: str):
#     return await search_papers(query)

@app.get("/search")
async def search(query: str, filter_type: str = "all"):
    return await search_papers(query, filter_type)
