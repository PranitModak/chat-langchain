from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from backend.retrieval_graph.graph import graph
import os
import json
from uuid import uuid4
from typing import Dict, Any

app = FastAPI()

# Allow CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

THREADS_FILE = "threads.json"

def load_threads() -> Dict[str, Any]:
    if not os.path.exists(THREADS_FILE):
        return {}
    with open(THREADS_FILE, "r") as f:
        return json.load(f)

def save_threads(threads: Dict[str, Any]):
    with open(THREADS_FILE, "w") as f:
        json.dump(threads, f)

@app.post("/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    # Pass the request data to the graph. Adapt as needed for your input format.
    result = await graph.ainvoke(data)
    return result

@app.post("/api/threads")
async def create_thread(request: Request):
    data = await request.json()
    user_id = data.get("metadata", {}).get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    threads = load_threads()
    thread_id = str(uuid4())
    threads[thread_id] = {
        "thread_id": thread_id,
        "metadata": {"user_id": user_id},
        "values": {"messages": []},
    }
    save_threads(threads)
    return threads[thread_id]

@app.post("/api/threads/search")
async def search_threads(request: Request):
    data = await request.json()
    user_id = data.get("metadata", {}).get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    threads = load_threads()
    result = [t for t in threads.values() if t["metadata"].get("user_id") == user_id]
    return result

@app.get("/api/threads/{thread_id}")
async def get_thread(thread_id: str):
    threads = load_threads()
    thread = threads.get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8080, reload=True) 