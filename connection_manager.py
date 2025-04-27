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
    verify_file_integrity,
    encrypt_file_with_chacha,
    generate_chacha_key,
    decrypt_file_with_chacha
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
    
    def register_room_settings(self, secret_key: str, settings: Dict[str, Any]) -> None:
        """Register settings for a room."""
        if secret_key not in self.room_settings:
            self.room_settings[secret_key] = {}
        
        # Update room settings with the new values
        self.room_settings[secret_key].update(settings)
        logger.info(f"Registered room settings for {secret_key[:8]}...")

    async def connect(self, websocket: WebSocket, secret_key: str, role: str) -> bool:
        """Connect a client to the room."""
        await websocket.accept()
        
        # Initialize the set of connections for this secret key if needed
        if secret_key not in self.active_connections:
            self.active_connections[secret_key] = set()
        
        # Check if we have room settings and enforce max_receivers if needed
        if role == "receiver" and secret_key in self.room_settings:
            max_receivers = self.room_settings[secret_key].get("max_receivers", 0)
            if max_receivers > 0:
                # Count existing receivers
                current_receivers = sum(1 for ws in self.active_connections[secret_key] 
                                     if self.connection_info.get(ws, {}).get("role") == "receiver")
                
                # Check if we've reached the limit
                if current_receivers >= max_receivers:
                    await websocket.send_json({
                        "type": "error", 
                        "message": f"Maximum number of receivers ({max_receivers}) already reached"
                    })
                    await websocket.close(code=1008, reason="Maximum receivers reached")
                    return False
        
        # Add the connection
        self.active_connections[secret_key].add(websocket)
        self.connection_info[websocket] = {"role": role, "secret_key": secret_key}
        
        # Send welcome message to the new connection
        await websocket.send_json({
            "type": "connected",
            "role": role,
            "message": f"Connected as {role}"
        })
        
        # Notify others about the new connection
        client_count = len(self.active_connections[secret_key])
        logger.info(f"Client connected to room {secret_key[:8]}... as {role}. Total clients: {client_count}")
        
        # Broadcast updated participant counts
        await self.broadcast_room_status(secret_key)
        
        return True
        
    async def disconnect(self, websocket: WebSocket) -> None:
        """Disconnect a client from the room."""
        if websocket not in self.connection_info:
            return
            
        info = self.connection_info[websocket]
        secret_key = info["secret_key"]
        role = info["role"]
        
        # Remove the connection
        if secret_key in self.active_connections:
            self.active_connections[secret_key].discard(websocket)
            
            # If no connections left in the room, clean up
            if not self.active_connections[secret_key]:
                self.active_connections.pop(secret_key, None)
                self.active_transfers.pop(secret_key, None)
                self.file_chunks.pop(secret_key, None)
                self.encryption_info.pop(secret_key, None)
                logger.info(f"Room {secret_key[:8]}... closed as last client disconnected")
            else:
                # Broadcast updated participant counts
                await self.broadcast_room_status(secret_key)
                logger.info(f"Client disconnected from room {secret_key[:8]}... as {role}")
        
        # Remove connection info
        self.connection_info.pop(websocket, None)
    
    async def broadcast_room_status(self, secret_key: str) -> None:
        """Broadcast room status to all connected clients."""
        if secret_key not in self.active_connections:
            return
            
        # Count participants by role
        senders = 0
        receivers = 0
        for ws in self.active_connections[secret_key]:
            info = self.connection_info.get(ws, {})
            if info.get("role") == "sender":
                senders += 1
            elif info.get("role") == "receiver":
                receivers += 1
        
        # Get room settings
        room_settings = self.room_settings.get(secret_key, {})
        max_receivers = room_settings.get("max_receivers", 0)
        
        # Create room status message
        status_message = {
            "type": "room_status",
            "senders": senders,
            "receivers": receivers,
            "max_receivers": max_receivers
        }
        
        # Broadcast to all in the room
        await self.broadcast(self.active_connections[secret_key], status_message)

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
        
        # Initialize encryption info based on method
        encryption_method = encryption_options.get("method") if encryption_options else "aes-256-gcm"
        
        if encryption_method == "aes-256-gcm":
            # Generate AES encryption keys and parameters ahead of time
            aes_key = generate_aes_key()
            self.encryption_info[secret_key] = {
                "aes_key": aes_key,
                "method": "aes-256-gcm"
            }
            logger.info(f"Generated AES encryption keys for transfer of {filename}")
        elif encryption_method == "chacha20-poly1305":
            # Generate ChaCha20 key
            chacha_key = generate_chacha_key()
            self.encryption_info[secret_key] = {
                "chacha_key": chacha_key,
                "method": "chacha20-poly1305"
            }
            logger.info(f"Generated ChaCha20-Poly1305 encryption keys for transfer of {filename}")
        else:
            # Default to AES if unknown method
            aes_key = generate_aes_key()
            self.encryption_info[secret_key] = {
                "aes_key": aes_key,
                "method": "aes-256-gcm"
            }
            logger.warning(f"Unknown encryption method '{encryption_method}', defaulting to AES-256-GCM")
        
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
            
            # Encrypt the file based on the specified method
            encrypted_data = None
            encryption_metadata = {}
            encryption_method = encryption_options.get("method", "aes-256-gcm")
            
            if encryption_method == "aes-256-gcm" and secret_key in self.encryption_info:
                # Get the prepared encryption key
                aes_key = self.encryption_info[secret_key]["aes_key"]
                
                # Encrypt the entire file with AES
                encrypted_package = encrypt_file_with_aes(complete_file_data, aes_key)
                encrypted_data = encrypted_package['encrypted_data']
                
                # Store encryption metadata
                encryption_metadata = {
                    "method": "aes-256-gcm",
                    "aes_key": aes_key.hex(),
                    "iv": encrypted_package['iv'].hex(),
                    "tag": encrypted_package['tag'].hex(),
                }
                
                if file_hash:
                    encryption_metadata["file_hash"] = file_hash
                
                logger.info(f"File encryption completed for {transfer['filename']} using AES-256-GCM")
                
            elif encryption_method == "chacha20-poly1305" and secret_key in self.encryption_info:
                # Get the prepared ChaCha20 key
                chacha_key = self.encryption_info[secret_key]["chacha_key"]
                
                # Encrypt the entire file with ChaCha20-Poly1305
                encrypted_package = encrypt_file_with_chacha(complete_file_data, chacha_key)
                encrypted_data = encrypted_package['encrypted_data']
                
                # Store encryption metadata
                encryption_metadata = {
                    "method": "chacha20-poly1305",
                    "chacha_key": chacha_key.hex(),
                    "nonce": encrypted_package['nonce'].hex(),
                }
                
                if file_hash:
                    encryption_metadata["file_hash"] = file_hash
                
                logger.info(f"File encryption completed for {transfer['filename']} using ChaCha20-Poly1305")
            
            else:
                # If no valid encryption method, use the original data (not encrypted)
                encrypted_data = complete_file_data
                logger.warning(f"No valid encryption method found, sending unencrypted data")
            
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
