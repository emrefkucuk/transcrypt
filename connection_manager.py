import json
from fastapi import WebSocket
from typing import Dict, Set, Optional, List
from starlette.websockets import WebSocketState
import logging
import asyncio
from encr import (
    encrypt_file_with_aes,
    generate_aes_key,
    decrypt_file_with_aes,
    calculate_file_hash,
    verify_file_integrity
)

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Secret key -> set of active connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Secret key -> file metadata
        self.active_transfers: Dict[str, Dict] = {}
        # WebSocket -> {'role': 'sender'|'receiver', 'secret_key': str}
        self.connection_info: Dict[WebSocket, Dict] = {}
        
    async def connect(self, websocket: WebSocket, secret_key: str, role: str):
        await websocket.accept()
        
        if secret_key not in self.active_connections:
            self.active_connections[secret_key] = set()
            
        self.active_connections[secret_key].add(websocket)
        self.connection_info[websocket] = {"role": role, "secret_key": secret_key}
        
        logger.info(f"New {role} connection with key {secret_key[:5]}... established")
        
        # Notify about connection status
        await self.send_room_status(secret_key)
    
    async def disconnect(self, websocket: WebSocket):
        if websocket in self.connection_info:
            info = self.connection_info[websocket]
            secret_key = info["secret_key"]
            
            if secret_key in self.active_connections:
                self.active_connections[secret_key].discard(websocket)
                
                # If room is empty, clean up
                if not self.active_connections[secret_key]:
                    self.active_connections.pop(secret_key, None)
                    self.active_transfers.pop(secret_key, None)
                else:
                    # Notify remaining participants
                    await self.send_room_status(secret_key)
            
            self.connection_info.pop(websocket, None)
            logger.info(f"Connection with role {info['role']} disconnected")
    
    async def send_room_status(self, secret_key: str):
        if secret_key not in self.active_connections:
            return
            
        connections = self.active_connections[secret_key]
        
        # Count senders and receivers
        senders = sum(1 for ws in connections if self.connection_info.get(ws, {}).get("role") == "sender")
        receivers = sum(1 for ws in connections if self.connection_info.get(ws, {}).get("role") == "receiver")
        
        status_message = {
            "type": "status",
            "senders": senders,
            "receivers": receivers,
            "ready_to_transfer": senders > 0 and receivers > 0
        }
        
        await self.broadcast(connections, status_message)

    async def start_file_transfer(self, websocket: WebSocket, filename: str, filesize: int, encryption_options=None):
        if websocket not in self.connection_info:
            return False
            
        info = self.connection_info[websocket]
        secret_key = info["secret_key"]
        
        if info["role"] != "sender":
            await websocket.send_json({"type": "error", "message": "Only sender can initiate file transfer"})
            return False
        
        self.active_transfers[secret_key] = {
            "filename": filename,
            "filesize": filesize,
            "transferred": 0,
            "encryption_options": encryption_options or {
                "method": "aes-256-gcm",
                "integrityCheck": True
            }
        }
        
        transfer_info = {
            "type": "transfer_start",
            "filename": filename,
            "filesize": filesize,
            "encryptionOptions": encryption_options
        }
        
        await self.broadcast(self.active_connections[secret_key], transfer_info)
        return True
    
    async def send_file_chunk(self, websocket: WebSocket, chunk_data: bytes, chunk_id: int, total_chunks: int):
        if websocket not in self.connection_info:
            return False
            
        info = self.connection_info[websocket]
        secret_key = info["secret_key"]
        
        if secret_key not in self.active_connections or secret_key not in self.active_transfers:
            return False
            
        # Get transfer info and encryption options
        transfer = self.active_transfers[secret_key]
        encryption_options = transfer.get("encryption_options", {})
        chunk_size = len(chunk_data)
        
        # Apply encryption if specified
        processed_chunk = chunk_data
        encryption_metadata = {}
        
        # İlk chunk'sa ve şifreleme isteniyorsa şifrele
        if chunk_id == 0 and encryption_options.get("method") == "aes-256-gcm":
            # AES ile şifrele
            aes_key = generate_aes_key()
            encrypted_package = encrypt_file_with_aes(chunk_data, aes_key)
            processed_chunk = encrypted_package['encrypted_data']
            
            # Metadata içinde AES anahtarı ve diğer bilgileri gönder
            encryption_metadata = {
                "aes_key": aes_key.hex(),
                "iv": encrypted_package['iv'].hex(),
                "tag": encrypted_package['tag'].hex(),
            }
            
            # Log ekleyin
            logger.info(f"File encryption applied with AES-256-GCM for {transfer['filename']}")
        
        # Calculate hash for integrity check if requested
        if encryption_options.get("integrityCheck", True):
            chunk_hash = calculate_file_hash(chunk_data)
            encryption_metadata["chunk_hash"] = chunk_hash
            
            # Son chunk için bütünlük doğrulama logunu ekle
            if chunk_id == total_chunks - 1:
                logger.info(f"Final integrity hash calculated for {transfer['filename']}: {chunk_hash[:15]}...")
        
        # Update transferred amount
        transfer["transferred"] += chunk_size
        
        # Send to all receivers
        receivers = [ws for ws in self.active_connections[secret_key] 
                     if self.connection_info.get(ws, {}).get("role") == "receiver"]
        
        for receiver in receivers:
            if receiver.client_state == WebSocketState.CONNECTED:
                try:
                    # Processed chunk gönder (şifrelenmiş veya normal)
                    await receiver.send_bytes(processed_chunk)
                    
                    # Send progress and encryption info as JSON
                    progress_info = {
                        "type": "transfer_progress",
                        "chunk_id": chunk_id,
                        "total_chunks": total_chunks,
                        "transferred": transfer["transferred"],
                        "total": transfer["filesize"],
                        "percentage": min(100, int((transfer["transferred"] / transfer["filesize"]) * 100)),
                        "encryption_metadata": encryption_metadata
                    }
                    await receiver.send_json(progress_info)
                except Exception as e:
                    logger.error(f"Error sending to receiver: {str(e)}")
        
        # Send progress to sender as well
        progress_info = {
            "type": "transfer_progress",
            "chunk_id": chunk_id,
            "total_chunks": total_chunks,
            "transferred": transfer["transferred"],
            "total": transfer["filesize"],
            "percentage": min(100, int((transfer["transferred"] / transfer["filesize"]) * 100))
        }
        await websocket.send_json(progress_info)
        
        # If transfer complete
        if chunk_id == total_chunks - 1:
            complete_info = {
                "type": "transfer_complete",
                "filename": transfer["filename"],
                "filesize": transfer["filesize"]
            }
            
            # Bütünlük doğrulaması için son hash'i ekle
            if encryption_options.get("integrityCheck", True):
                complete_info["integrity_verified"] = True
                complete_info["integrity_hash"] = encryption_metadata.get("chunk_hash", "")
                
            await self.broadcast(self.active_connections[secret_key], complete_info)
            
        return True

    async def broadcast(self, connections: Set[WebSocket], message: Dict):
        for connection in connections.copy():
            if connection.client_state == WebSocketState.CONNECTED:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting message: {str(e)}")
