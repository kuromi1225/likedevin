import os
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import git
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import aiofiles

# --- Configuration ---
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://ollama:11434")
WORKSPACE_PATH = "/app/workspace"

# --- FastAPI App ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Data Models ---
class TaskRequest(BaseModel):
    prompt: str

class GitCloneRequest(BaseModel):
    repo_url: str

class Settings(BaseModel):
    llm_model: str

# --- Global State (for simplicity, replace with a proper DB later) ---
current_settings = {"llm_model": "llama3"}
active_connections: list[WebSocket] = []

# --- WebSocket Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# --- File System Watcher ---
class WorkspaceEventHandler(FileSystemEventHandler):
    async def on_any_event(self, event):
        await manager.broadcast(json.dumps({"type": "filesystem_change", "event": event.event_type, "path": event.src_path}))

async def start_workspace_watcher():
    observer = Observer()
    event_handler = WorkspaceEventHandler()
    observer.schedule(event_handler, WORKSPACE_PATH, recursive=True)
    observer.start()
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

# --- Agent Logic ---
async def run_agent_task(prompt: str):
    """
    Simplified agent logic. Decomposes a task and "executes" it.
    """
    await manager.broadcast(json.dumps({"type": "thought", "content": "Thinking about the task..."}))
    
    # 1. Decompose task using Ollama
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OLLAMA_API_URL}/api/generate",
                json={
                    "model": current_settings["llm_model"],
                    "prompt": f"Decompose the following task into a series of simple steps: {prompt}"
                },
                timeout=60.0,
            )
            response.raise_for_status()
            
            # Stream the response and parse subtasks
            subtasks_text = ""
            for line in response.text.splitlines():
                subtasks_text += json.loads(line).get("response", "")

            subtasks = [s.strip() for s in subtasks_text.split('\n') if s.strip()]
            await manager.broadcast(json.dumps({"type": "subtasks", "tasks": subtasks}))

            # 2. "Execute" subtasks
            for i, subtask in enumerate(subtasks):
                await manager.broadcast(json.dumps({"type": "subtask_status", "task_index": i, "status": "running"}))
                await asyncio.sleep(2) # Simulate work
                await manager.broadcast(json.dumps({"type": "command_result", "command": subtask, "output": "Done."}))
                await manager.broadcast(json.dumps({"type": "subtask_status", "task_index": i, "status": "completed"}))

    except httpx.RequestError as e:
        await manager.broadcast(json.dumps({"type": "error", "content": f"Failed to connect to Ollama: {e}"}))
    except Exception as e:
        await manager.broadcast(json.dumps({"type": "error", "content": str(e)}))


# --- API Endpoints ---
@app.post("/api/task/start")
async def task_start(request: TaskRequest):
    asyncio.create_task(run_agent_task(request.prompt))
    return {"message": "Task started"}

@app.post("/api/git/clone")
async def git_clone(request: GitCloneRequest):
    try:
        # Basic security: prevent directory traversal
        repo_name = request.repo_url.split('/')[-1].replace('.git', '')
        clone_path = os.path.join(WORKSPACE_PATH, repo_name)
        
        if os.path.exists(clone_path):
             return {"message": f"Directory {repo_name} already exists."}

        await manager.broadcast(json.dumps({"type": "log", "content": f"Cloning {request.repo_url} into {clone_path}"}))
        git.Repo.clone_from(request.repo_url, clone_path)
        await manager.broadcast(json.dumps({"type": "log", "content": "Cloning complete."}))
        return {"message": "Repository cloned successfully"}
    except Exception as e:
        await manager.broadcast(json.dumps({"type": "error", "content": str(e)}))
        return {"error": str(e)}

@app.get("/api/settings")
async def get_settings():
    return current_settings

@app.post("/api/settings")
async def update_settings(settings: Settings):
    current_settings.update(settings.dict())
    await manager.broadcast(json.dumps({"type": "settings_updated", "settings": current_settings}))
    return {"message": "Settings updated"}

@app.get("/api/files")
async def list_files(path: str = "."):
    full_path = os.path.join(WORKSPACE_PATH, path)
    if not os.path.exists(full_path):
        return {"error": "Path not found"}
    
    items = []
    for item in os.listdir(full_path):
        item_path = os.path.join(full_path, item)
        items.append({
            "name": item,
            "is_dir": os.path.isdir(item_path),
            "path": os.path.relpath(item_path, WORKSPACE_PATH)
        })
    return items

# --- WebSocket Endpoint ---
@app.websocket("/ws/agent")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # This is for receiving messages from client if needed
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- Server Startup ---
@app.on_event("startup")
async def startup_event():
    # Create workspace if it doesn't exist
    if not os.path.exists(WORKSPACE_PATH):
        os.makedirs(WORKSPACE_PATH)
    # Start the file watcher in the background
    asyncio.create_task(start_workspace_watcher())