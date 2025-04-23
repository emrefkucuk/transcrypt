import json
from fastapi import WebSocket
from typing import Dict, Set, Optional, List, Any
from starlette.websockets import WebSocketState
import logging
import asyncio
import io
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
        # Store file chunks for complete files
        self.file_chunks: Dict[str, Dict[int, bytes]] = {}
        # Store encryption info
        self.encryption_info: Dict[str, Dict] = {}
        # Store room settings
        self.room_settings: Dict[str, Dict] = {}
        
    async def connect(self, websocket: WebSocket, secret_key: str, role: str):
        # Check if room exists
        if secret_key not in self.active_connections and secret_key not in self.room_settings:
            await websocket.accept()
            await websocket.send_json({
                "type": "error",
                "message": "Room does not exist"
            })
            await websocket.close()
            return False
        
        # Check if room is at capacity for receivers
        if role == "receiver" and secret_key in self.room_settings:
            max_receivers = self.room_settings[secret_key].get("max_receivers", 0)
            current_receivers = sum(1 for ws in self.active_connections.get(secret_key, set()) 
                                   if self.connection_info.get(ws, {}).get("role") == "receiver")
            
            if max_receivers > 0 and current_receivers >= max_receivers:
                # Room is full, reject connection
                await websocket.accept()
                await websocket.send_json({
                    "type": "error",
                    "message": "Room has reached maximum capacity"
                })
                await websocket.close()
                return False
        
        await websocket.accept()
        
        if secret_key not in self.active_connections:
            self.active_connections[secret_key] = set()
            
        self.active_connections[secret_key].add(websocket)
        self.connection_info[websocket] = {"role": role, "secret_key": secret_key}
        
        logger.info(f"New {role} connection with key {secret_key[:5]}... established")
        
        # Notify about connection status
        await self.send_room_status(secret_key)
        return True
    
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
                    self.file_chunks.pop(secret_key, None)
                    self.encryption_info.pop(secret_key, None)
                    self.room_settings.pop(secret_key, None)
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
        
        # Get max receivers setting
        max_receivers = 0
        if secret_key in self.room_settings:
            max_receivers = self.room_settings[secret_key].get("max_receivers", 0)
            
        status_message = {
            "type": "status",
            "senders": senders,
            "receivers": receivers,
            "max_receivers": max_receivers,
            "ready_to_transfer": senders > 0 and receivers > 0
        }
        
        await self.broadcast(connections, status_message)

    def register_room_settings(self, secret_key: str, settings: Dict[str, Any]) -> None:
        """
        Register settings for a room.
        
        Args:
            secret_key: The room's secret key
            settings: Dictionary of room settings (max_receivers, etc.)
        """
        if secret_key not in self.room_settings:
            self.room_settings[secret_key] = {}
            
        # Update with new settings
        self.room_settings[secret_key].update(settings)
        logger.info(f"Room settings updated for {secret_key[:5]}... - max_receivers: {settings.get('max_receivers', 0)}")

    async def start_file_transfer(self, websocket: WebSocket, filename: str, filesize: int, encryption_options=None):
        if websocket not in self.connection_info:
            return False
            
        info = self.connection_info[websocket]
        secret_key = info["secret_key"]
        
        if info["role"] != "sender":
            await websocket.send_json({"type": "error", "message": "Only sender can initiate file transfer"})
            return False
        
        # Log the filename for debugging
        logger.info(f"Starting transfer of file: {filename} ({filesize} bytes)")
        
        self.active_transfers[secret_key] = {
            "filename": filename,
            "filesize": filesize,
            "transferred": 0,
            "encryption_options": encryption_options or {
                "method": "aes-256-gcm",
                "integrityCheck": True
            }
        }
        
        # Initialize chunk storage for this file transfer
        self.file_chunks[secret_key] = {}
        
        # Initialize encryption info
        if encryption_options and encryption_options.get("method") == "aes-256-gcm":
            # Generate encryption keys and parameters ahead of time
            aes_key = generate_aes_key()
            self.encryption_info[secret_key] = {
                "aes_key": aes_key,
                "method": "aes-256-gcm"
            }
            logger.info(f"Generated encryption keys for transfer of {filename}")
        
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
        
        # Store the chunk
        if secret_key not in self.file_chunks:
            self.file_chunks[secret_key] = {}
        self.file_chunks[secret_key][chunk_id] = chunk_data
        
        # Update transferred amount
        transfer["transferred"] += chunk_size
        
        # Calculate progress
        progress_percentage = min(100, int((transfer["transferred"] / transfer["filesize"]) * 100))
        
        # If we've collected all chunks, process the complete file
        if len(self.file_chunks[secret_key]) == total_chunks and chunk_id == total_chunks - 1:
            # This is the last chunk, process the complete file
            complete_file_data = self._assemble_file_chunks(secret_key, total_chunks)
            
            # Calculate hash for integrity check (before encryption)
            file_hash = None
            if encryption_options.get("integrityCheck", True):
                file_hash = calculate_file_hash(complete_file_data)
                logger.info(f"Calculated integrity hash for complete file: {file_hash[:15]}...")
            
            # Encrypt the file if needed
            encrypted_data = None
            encryption_metadata = {}
            
            if encryption_options.get("method") == "aes-256-gcm" and secret_key in self.encryption_info:
                # Get the prepared encryption key
                aes_key = self.encryption_info[secret_key]["aes_key"]
                
                # Encrypt the entire file
                encrypted_package = encrypt_file_with_aes(complete_file_data, aes_key)
                encrypted_data = encrypted_package['encrypted_data']
                
                # Store encryption metadata
                encryption_metadata = {
                    "aes_key": aes_key.hex(),
                    "iv": encrypted_package['iv'].hex(),
                    "tag": encrypted_package['tag'].hex(),
                }
                
                if file_hash:
                    encryption_metadata["file_hash"] = file_hash
                
                logger.info(f"File encryption completed for {transfer['filename']}")
            
            # Send the processed file to all receivers
            receivers = [ws for ws in self.active_connections[secret_key] 
                        if self.connection_info.get(ws, {}).get("role") == "receiver"]
            
            for receiver in receivers:
                if receiver.client_state == WebSocketState.CONNECTED:
                    try:
                        # Send the file data (encrypted or plain)
                        data_to_send = encrypted_data if encrypted_data is not None else complete_file_data
                        await receiver.send_bytes(data_to_send)
                        
                        # Send file metadata
                        progress_info = {
                            "type": "transfer_progress",
                            "chunk_id": chunk_id,
                            "total_chunks": total_chunks,
                            "transferred": transfer["filesize"],
                            "total": transfer["filesize"],
                            "percentage": 100,
                            "encryption_metadata": encryption_metadata
                        }
                        await receiver.send_json(progress_info)
                        
                        # Complete transfer notification
                        complete_info = {
                            "type": "transfer_complete",
                            "filename": transfer["filename"],
                            "filesize": transfer["filesize"]
                        }
                        
                        # Add integrity verification info
                        if file_hash:
                            complete_info["integrity_verified"] = True
                            complete_info["integrity_hash"] = file_hash
                            
                        await receiver.send_json(complete_info)
                        
                    except Exception as e:
                        logger.error(f"Error sending to receiver: {str(e)}")
            
            # Send progress to sender as well
            progress_info = {
                "type": "transfer_progress",
                "chunk_id": chunk_id,
                "total_chunks": total_chunks,
                "transferred": transfer["filesize"],
                "total": transfer["filesize"],
                "percentage": 100
            }
            await websocket.send_json(progress_info)
            
            # Send completion to sender
            complete_info = {
                "type": "transfer_complete",
                "filename": transfer["filename"],
                "filesize": transfer["filesize"]
            }
            
            if file_hash:
                complete_info["integrity_verified"] = True
                complete_info["integrity_hash"] = file_hash
                
            await websocket.send_json(complete_info)
            
            # Clean up
            self.file_chunks.pop(secret_key, None)
            self.encryption_info.pop(secret_key, None)
            
        else:
            # This is not the last chunk or not all chunks received yet
            # Just send a progress update to sender
            progress_info = {
                "type": "transfer_progress",
                "chunk_id": chunk_id,
                "total_chunks": total_chunks,
                "transferred": transfer["transferred"],
                "total": transfer["filesize"],
                "percentage": progress_percentage
            }
            await websocket.send_json(progress_info)
            
            # Send progress to receivers
            receivers = [ws for ws in self.active_connections[secret_key] 
                       if self.connection_info.get(ws, {}).get("role") == "receiver"]
            
            for receiver in receivers:
                if receiver.client_state == WebSocketState.CONNECTED:
                    await receiver.send_json(progress_info)
            
        return True
    
    def _assemble_file_chunks(self, secret_key: str, total_chunks: int) -> bytes:
        """Assemble all chunks into a complete file."""
        if secret_key not in self.file_chunks:
            return b''
        
        # Create a bytes buffer
        file_buffer = io.BytesIO()
        
        # Write chunks in order
        for i in range(total_chunks):
            if i in self.file_chunks[secret_key]:
                file_buffer.write(self.file_chunks[secret_key][i])
        
        # Return the complete file data
        return file_buffer.getvalue()

    async def broadcast(self, connections: Set[WebSocket], message: Dict):
        for connection in connections.copy():
            if connection.client_state == WebSocketState.CONNECTED:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting message: {str(e)}")
