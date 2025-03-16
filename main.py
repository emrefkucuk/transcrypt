import logging
import os
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional, Dict, Any, List
import uvicorn

from connection_manager import ConnectionManager
from security import generate_secret_key, verify_secret_key

# Logging yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Secure File Transfer API")

# Static dosyaları sunmak için
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Aktif secret keyleri saklayacak dictionary
active_keys: Dict[str, Dict[str, Any]] = {}
manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def get_home():
    with open(os.path.join(static_dir, "index.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/create-room")
async def create_room():
    """Yeni bir dosya transfer odası oluşturur ve secret key döndürür"""
    secret_key = generate_secret_key()
    active_keys[secret_key] = {"created_at": "now", "last_activity": "now"}
    
    return JSONResponse(content={
        "status": "success", 
        "secret_key": secret_key,
        "message": "Room created successfully"
    })

@app.get("/api/check-room")
async def check_room(secret_key: str = Query(...)):
    """Verilen secret key'in geçerli olup olmadığını kontrol eder"""
    if secret_key in active_keys:
        return JSONResponse(content={"status": "success", "valid": True})
    return JSONResponse(content={"status": "success", "valid": False})

@app.websocket("/ws/sender/{secret_key}")
async def websocket_sender_endpoint(websocket: WebSocket, secret_key: str):
    """Dosya gönderenler için WebSocket endpoint'i"""
    if secret_key not in active_keys:
        await websocket.close(code=1008, reason="Invalid secret key")
        return
    
    await manager.connect(websocket, secret_key, "sender")
    
    try:
        while True:
            # Text veya binary mesaj alabiliriz
            message = await websocket.receive()
            
            # Text mesajı - genellikle kontrol mesajları JSON formatında
            if "text" in message:
                try:
                    data = json.loads(message["text"])
                    if data.get("type") == "start_transfer":
                        filename = data.get("filename", "unknown_file")
                        filesize = data.get("filesize", 0)
                        encryption_options = data.get("encryptionOptions", {})
                        await manager.start_file_transfer(websocket, filename, filesize, encryption_options)
                except json.JSONDecodeError:
                    continue
            
            # Binary mesajı - dosya parçaları
            elif "bytes" in message:
                chunk_data = message["bytes"]
                # Assume additional metadata is sent in the next text message
                metadata = await websocket.receive_json()
                chunk_id = metadata.get("chunk_id", 0)
                total_chunks = metadata.get("total_chunks", 1)
                await manager.send_file_chunk(websocket, chunk_data, chunk_id, total_chunks)
                
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await manager.disconnect(websocket)

@app.websocket("/ws/receiver/{secret_key}")
async def websocket_receiver_endpoint(websocket: WebSocket, secret_key: str):
    """Dosya alanlar için WebSocket endpoint'i"""
    if secret_key not in active_keys:
        await websocket.close(code=1008, reason="Invalid secret key")
        return
    
    await manager.connect(websocket, secret_key, "receiver")
    
    try:
        while True:
            # Alıcılar genellikle sadece kontrol mesajları gönderir
            data = await websocket.receive_json()
            # Handle any specific receiver messages if needed
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
