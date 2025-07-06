import os
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import git
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import aiofiles

# --- 設定 (Configuration) ---
# 環境変数からOllamaのURLを取得。なければデフォルト値を使用。
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://ollama:11434")
# エージェントが作業するワークスペースのパス
WORKSPACE_PATH = "/app/workspace"

# --- FastAPIアプリケーションの初期化 ---
app = FastAPI()

# --- CORSミドルウェアの設定 ---
# フロントエンドからのリクエストを許可するために必要
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では特定のオリジンに制限してください
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- データモデル (Pydantic) ---
# APIリクエストの型定義
class TaskRequest(BaseModel):
    prompt: str

class GitCloneRequest(BaseModel):
    repo_url: str

class FileContent(BaseModel):
    path: str
    content: str

class Settings(BaseModel):
    llm_model: str

# --- グローバル変数 (簡易的な状態管理) ---
# 本来はデータベースなどで管理するのが望ましい
current_settings = {"llm_model": "llama3"} #
agent_connections: list[WebSocket] = []
ask_connections: list[WebSocket] = []

# --- WebSocket接続マネージャー ---
class ConnectionManager:
    def __init__(self):
        self.agent_connections: list[WebSocket] = []
        self.ask_connections: list[WebSocket] = []

    async def connect_agent(self, websocket: WebSocket):
        await websocket.accept()
        self.agent_connections.append(websocket)

    def disconnect_agent(self, websocket: WebSocket):
        self.agent_connections.remove(websocket)

    async def connect_ask(self, websocket: WebSocket):
        await websocket.accept()
        self.ask_connections.append(websocket)

    def disconnect_ask(self, websocket: WebSocket):
        self.ask_connections.remove(websocket)

    async def broadcast_agent(self, message: dict):
        for connection in self.agent_connections:
            await connection.send_text(json.dumps(message))

    async def send_ask(self, question: str) -> str:
        if not self.ask_connections:
            # 確認モード(Ask)の接続がない場合は、デフォルトで「yes」とみなす
            await self.broadcast_agent({"type": "log", "content": "Ask connection not found, proceeding with 'yes'"})
            return "yes"

        question_message = {"type": "ask", "question": question}
        for connection in self.ask_connections:
            await connection.send_text(json.dumps(question_message))
        
        # 最初のask接続からの応答を待つ
        response_socket = self.ask_connections[0]
        try:
            # タイムアウトを設定することも検討
            response_text = await response_socket.receive_text()
            response_data = json.loads(response_text)
            return response_data.get("answer", "no")
        except WebSocketDisconnect:
            self.disconnect_ask(response_socket)
            return "no" # 切断された場合は "no" とする

manager = ConnectionManager()

# --- ファイルシステム監視 ---
class WorkspaceEventHandler(FileSystemEventHandler):
    async def on_any_event(self, event):
        # ファイルシステムの変更をフロントエンドに通知
        await manager.broadcast_agent({"type": "filesystem_change", "event": event.event_type, "path": event.src_path})

async def start_workspace_watcher():
    if not os.path.exists(WORKSPACE_PATH):
        os.makedirs(WORKSPACE_PATH)
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

# --- エージェントロジック ---
async def run_agent_task(prompt: str):
    """
    タスクを実行するメインの非同期関数。
    Devinのように、思考、計画、実行のサイクルを模倣します。
    """
    await manager.broadcast_agent({"type": "thought", "content": f"受け取ったタスク: {prompt}"})
    await asyncio.sleep(1)
    
    # 1. タスクをサブタスクに分解する (LLMを使用)
    await manager.broadcast_agent({"type": "thought", "content": "タスクをサブタスクに分解しています..."})
    
    decomposition_prompt = f"""
    You are an expert programmer and problem solver. Decompose the following high-level task into a series of simple, executable steps (subtasks) for a junior developer.
    The subtasks should be a numbered list. For example:
    1. Create a file named 'hello.py'.
    2. Write 'print("Hello, World!")' into 'hello.py'.
    3. Execute the python script 'hello.py'.

    High-level task: "{prompt}"
    
    Subtasks:
    """
    
    subtasks = []
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OLLAMA_API_URL}/api/generate",
                json={
                    "model": current_settings["llm_model"],
                    "prompt": decomposition_prompt,
                    "stream": False # ストリームではなく一括で受け取る
                },
                timeout=60.0,
            )
            response.raise_for_status()
            full_response = response.json().get("response", "")
            # レスポンスから番号付きリストを抽出
            subtasks = [s.strip() for s in full_response.split('\n') if s.strip() and s.strip()[0].isdigit()]

        if not subtasks:
             await manager.broadcast_agent({"type": "error", "content": "サブタスクの生成に失敗しました。"})
             return

        await manager.broadcast_agent({"type": "subtasks", "tasks": subtasks})

    except httpx.RequestError as e:
        await manager.broadcast_agent({"type": "error", "content": f"Ollamaへの接続に失敗しました: {e}"})
        return
    except Exception as e:
        await manager.broadcast_agent({"type": "error", "content": f"サブタスク分解中にエラーが発生しました: {str(e)}"})
        return

    # 2. 各サブタスクを順番に実行する
    for i, subtask in enumerate(subtasks):
        await manager.broadcast_agent({"type": "subtask_status", "task_index": i, "status": "running"})
        await manager.broadcast_agent({"type": "thought", "content": f"サブタスク実行中: {subtask}"})

        # --- ここにMaverickフレームワークの各ツールを呼び出すロジックを実装 ---
        # 例: ファイル作成、コード編集、コマンド実行など
        # Askモードの場合は、重要な操作の前にユーザーに確認を求める
        
        # answer = await manager.send_ask(f"'{subtask}' を実行してもよろしいですか？")
        # if answer.lower() != 'yes':
        #     await manager.broadcast_agent({"type": "log", "content": f"タスク '{subtask}' はユーザーによってキャンセルされました。"})
        #     await manager.broadcast_agent({"type": "subtask_status", "task_index": i, "status": "cancelled"})
        #     continue

        # (シミュレーション)
        await asyncio.sleep(2) 
        command_output = f"'{subtask}' を正常に実行しました。"
        
        await manager.broadcast_agent({"type": "command_result", "command": subtask, "output": command_output})
        await manager.broadcast_agent({"type": "subtask_status", "task_index": i, "status": "completed"})

    await manager.broadcast_agent({"type": "log", "content": "全てのタスクが完了しました。"})


# --- APIエンドポイント ---
@app.post("/api/task/start")
async def task_start(request: TaskRequest):
    # run_agent_taskをバックグラウンドで実行
    asyncio.create_task(run_agent_task(request.prompt))
    return {"message": "Task started"}

@app.post("/api/git/clone")
async def git_clone(request: GitCloneRequest):
    try:
        # ディレクトリトラバーサル対策
        repo_name = request.repo_url.split('/')[-1]
        if '.git' in repo_name:
            repo_name = repo_name.split('.git')[0]
        
        clone_path = os.path.join(WORKSPACE_PATH, repo_name)
        
        if os.path.exists(clone_path):
             return {"message": f"ディレクトリ '{repo_name}' は既に存在します。"}

        await manager.broadcast_agent({"type": "log", "content": f"'{request.repo_url}' をクローンしています..."})
        git.Repo.clone_from(request.repo_url, clone_path)
        await manager.broadcast_agent({"type": "log", "content": "クローンが完了しました。"})
        return {"message": "Repository cloned successfully"}
    except Exception as e:
        await manager.broadcast_agent({"type": "error", "content": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/settings")
async def get_settings():
    return current_settings

@app.post("/api/settings")
async def update_settings(settings: Settings):
    current_settings.update(settings.dict())
    await manager.broadcast_agent({"type": "settings_updated", "settings": current_settings})
    return {"message": "Settings updated"}

@app.get("/api/files")
async def list_files(path: str = "."):
    base_path = os.path.abspath(WORKSPACE_PATH)
    full_path = os.path.abspath(os.path.join(base_path, path))

    # パストラバーサル攻撃の防止
    if not full_path.startswith(base_path):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not os.path.exists(full_path) or not os.path.isdir(full_path):
        return {"error": "Path not found or not a directory"}
    
    items = []
    for item in sorted(os.listdir(full_path)):
        item_path = os.path.join(full_path, item)
        items.append({
            "name": item,
            "is_dir": os.path.isdir(item_path),
            "path": os.path.relpath(item_path, base_path)
        })
    return items

@app.get("/api/file")
async def read_file(path: str):
    base_path = os.path.abspath(WORKSPACE_PATH)
    full_path = os.path.abspath(os.path.join(base_path, path))

    if not full_path.startswith(base_path):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not os.path.exists(full_path) or os.path.isdir(full_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        async with aiofiles.open(full_path, mode='r', encoding='utf-8') as f:
            content = await f.read()
        return {"path": path, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {e}")

@app.post("/api/file")
async def write_file(file: FileContent):
    base_path = os.path.abspath(WORKSPACE_PATH)
    full_path = os.path.abspath(os.path.join(base_path, file.path))
    
    if not full_path.startswith(base_path):
        raise HTTPException(status_code=400, detail="Invalid path")
        
    try:
        # ディレクトリが存在しない場合は作成
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        async with aiofiles.open(full_path, mode='w', encoding='utf-8') as f:
            await f.write(file.content)
        await manager.broadcast_agent({"type": "log", "content": f"ファイルが保存されました: {file.path}"})
        return {"message": "File saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error writing file: {e}")

# --- WebSocketエンドポイント ---
@app.websocket("/ws/agent")
async def websocket_agent_endpoint(websocket: WebSocket):
    await manager.connect_agent(websocket)
    try:
        while True:
            await websocket.receive_text() # クライアントからのメッセージを待機
    except WebSocketDisconnect:
        manager.disconnect_agent(websocket)

@app.websocket("/ws/ask")
async def websocket_ask_endpoint(websocket: WebSocket):
    await manager.connect_ask(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_ask(websocket)

# --- サーバー起動時イベント ---
@app.on_event("startup")
async def startup_event():
    # ワークスペースディレクトリが存在しない場合は作成
    if not os.path.exists(WORKSPACE_PATH):
        os.makedirs(WORKSPACE_PATH)
    # ファイルシステム監視をバックグラウンドで開始
    asyncio.create_task(start_workspace_watcher())

if __name__ == "__main__":
    import uvicorn
    # サーバーを起動
    uvicorn.run(app, host="0.0.0.0", port=8000)