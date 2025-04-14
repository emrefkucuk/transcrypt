import logging
import os
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Depends, Body, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional, Dict, Any, List
import uvicorn
import binascii
import shutil
from pathlib import Path

from connection_manager import ConnectionManager
from security import generate_secret_key, verify_secret_key
# Import steganography functionality
from llm_steganography.integration import (
    generate_steganographic_invitation,
    extract_key_from_invitation,
    validate_invitation,
    generate_room_name
)
# Import image steganography functionality
from image_steganography import (
    hide_secret_key_in_image,
    extract_secret_key_from_image,
    get_supported_image_formats
)
# Import encryption functions
from encr import (
    encrypt_file_with_aes,
    decrypt_file_with_aes,
    generate_aes_key,
    calculate_file_hash
)

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

# Test için encrypt/decrypt edilmiş dosyaları saklayacağımız klasör
encrypted_files_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "encrypted_files")
os.makedirs(encrypted_files_dir, exist_ok=True)

# Encryption keys storage (for test purposes only - in production use secure storage)
encryption_keys = {}

# Aktif secret keyleri saklayacak dictionary
active_keys: Dict[str, Dict[str, Any]] = {}
manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def get_home():
    with open(os.path.join(static_dir, "index.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/secure-transfer", response_class=HTMLResponse)
async def get_secure_transfer():
    """Serve the new secure file transfer interface"""
    with open(os.path.join(static_dir, "secure_transfer.html"), "r", encoding="utf-8") as f:
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

# New API endpoints for steganography functionality
@app.post("/api/create-steganographic-room")
async def create_steganographic_room(data: Dict[str, Any] = Body({})):
    """Create a new room with a secret key hidden in natural language text"""
    try:
        # Get optional prompt if provided
        custom_prompt = data.get("prompt")
        
        # Generate room name
        room_name = generate_room_name()
        
        # Generate steganographic invitation with custom prompt if provided
        invitation_info = generate_steganographic_invitation(
            room_name=room_name,
            custom_prompt=custom_prompt
        )
        
        secret_key = invitation_info["secret_key"]
        active_keys[secret_key] = {"created_at": "now", "last_activity": "now"}
        
        logger.info(f"Created steganographic room with name: {room_name}")
        if custom_prompt:
            logger.info(f"Used custom prompt for steganography: {custom_prompt[:50]}...")
        
        return JSONResponse(content={
            "status": "success", 
            "secret_key": secret_key,
            "invitation_text": invitation_info["invitation_text"],
            "room_name": room_name,
            "message": "Steganographic room created successfully"
        })
    except Exception as e:
        logger.error(f"Error creating steganographic room: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating steganographic room: {str(e)}")

@app.post("/api/extract-secret-key")
async def extract_secret_key(data: Dict[str, Any] = Body(...)):
    """Extract a secret key from steganographic invitation text"""
    invitation_text = data.get("invitation_text", "")
    
    if not invitation_text:
        return JSONResponse(content={
            "status": "error", 
            "message": "No invitation text provided"
        }, status_code=400)
    
    try:
        extracted_key = extract_key_from_invitation(invitation_text)
        
        if not extracted_key:
            return JSONResponse(content={
                "status": "error", 
                "message": "Could not extract a valid secret key from the provided text"
            }, status_code=400)
        
        # Check if the extracted key is valid
        if extracted_key in active_keys:
            logger.info(f"Successfully extracted secret key from invitation text")
            return JSONResponse(content={
                "status": "success", 
                "secret_key": extracted_key,
                "message": "Secret key extracted successfully"
            })
        else:
            logger.warning(f"Extracted key is not valid for any active room")
            return JSONResponse(content={
                "status": "error", 
                "message": "Extracted key is not valid for any active room"
            }, status_code=400)
    except Exception as e:
        logger.error(f"Error extracting secret key: {str(e)}")
        return JSONResponse(content={
            "status": "error", 
            "message": f"Error extracting secret key: {str(e)}"
        }, status_code=500)

# Image Steganography Endpoints
@app.post("/api/create-image-stego-room")
async def create_image_stego_room(image: UploadFile = File(...)):
    """
    Create a new room with a secret key hidden in an uploaded image using LSB steganography.
    
    Args:
        image: The image file to hide the secret key in
        
    Returns:
        JSON response with room details and steganographic image
    """
    try:
        # Check if the uploaded file is an image
        content_type = image.content_type
        if not content_type or not content_type.startswith('image/'):
            return JSONResponse(content={
                "status": "error",
                "message": "Uploaded file is not an image"
            }, status_code=400)
        
        # Read the image data
        image_data = await image.read()
        
        # Generate a new secret key for the room
        secret_key = generate_secret_key()
        
        # Generate room name
        room_name = generate_room_name()
        
        # Hide the secret key in the image
        stego_result = hide_secret_key_in_image(image_data, secret_key)
        
        if stego_result["status"] != "success":
            return JSONResponse(content={
                "status": "error",
                "message": stego_result.get("message", "Failed to hide key in image")
            }, status_code=500)
            
        # Get steganographic image data
        stego_image_data = stego_result["stego_image_data"]
        
        # Save the steganographic image
        original_filename = image.filename
        name, ext = os.path.splitext(original_filename)
        stego_filename = f"stego_{generate_secret_key(12)}{ext}"
        stego_filepath = os.path.join(encrypted_files_dir, stego_filename)
        
        with open(stego_filepath, "wb") as f:
            f.write(stego_image_data)
        
        # Add the new key to active keys
        active_keys[secret_key] = {"created_at": "now", "last_activity": "now", "stego_image": stego_filename}
        
        logger.info(f"Created room with key hidden in image {stego_filename}")
        
        return JSONResponse(content={
            "status": "success",
            "secret_key": secret_key,
            "room_name": room_name,
            "stego_image": stego_filename,
            "message": "Room created successfully with key hidden in image",
            "original_image_name": original_filename,
        })
        
    except Exception as e:
        logger.error(f"Error creating image stego room: {str(e)}")
        return JSONResponse(content={
            "status": "error",
            "message": f"Error creating room: {str(e)}"
        }, status_code=500)

@app.get("/api/download-stego-image/{filename}")
async def download_stego_image(filename: str):
    """
    Download a steganographic image containing a hidden room key.
    
    Args:
        filename: The filename of the steganographic image
        
    Returns:
        The steganographic image file for download
    """
    try:
        # Check if the file exists
        stego_filepath = os.path.join(encrypted_files_dir, filename)
        if not os.path.exists(stego_filepath):
            raise HTTPException(status_code=404, detail="Steganographic image not found")
        
        # Return the file for download
        return FileResponse(
            path=stego_filepath,
            filename=filename,
            media_type="image/png"  # Default to PNG, but FileResponse will detect the actual type
        )
        
    except Exception as e:
        logger.error(f"Error downloading stego image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error downloading image: {str(e)}")

@app.post("/api/extract-key-from-image")
async def extract_key_from_image(image: UploadFile = File(...)):
    """
    Extract a secret key from an uploaded steganographic image.
    
    Args:
        image: The steganographic image containing a hidden key
        
    Returns:
        JSON response with the extracted secret key if successful
    """
    try:
        # Check if the uploaded file is an image
        content_type = image.content_type
        if not content_type or not content_type.startswith('image/'):
            return JSONResponse(content={
                "status": "error",
                "message": "Uploaded file is not an image"
            }, status_code=400)
        
        # Read the image data
        image_data = await image.read()
        
        # Extract the secret key from the image
        result = extract_secret_key_from_image(image_data)
        
        if result["status"] != "success":
            return JSONResponse(content={
                "status": "error",
                "message": result.get("message", "Failed to extract key from image")
            }, status_code=400)
        
        extracted_key = result["secret_key"]
        
        # Check if the extracted key is valid for an active room
        if extracted_key not in active_keys:
            return JSONResponse(content={
                "status": "error",
                "message": "Extracted key is not valid for any active room"
            }, status_code=400)
        
        logger.info(f"Successfully extracted key from image")
        
        return JSONResponse(content={
            "status": "success",
            "secret_key": extracted_key,
            "message": "Secret key extracted successfully"
        })
        
    except Exception as e:
        logger.error(f"Error extracting key from image: {str(e)}")
        return JSONResponse(content={
            "status": "error",
            "message": f"Error extracting key: {str(e)}"
        }, status_code=500)

@app.get("/api/supported-image-formats")
async def get_supported_formats():
    """
    Get a list of supported image formats for steganography.
    
    Returns:
        JSON response with list of supported formats
    """
    formats = get_supported_image_formats()
    return JSONResponse(content={
        "status": "success",
        "formats": formats
    })

# NEW TEST ENDPOINTS FOR ENCRYPTION/DECRYPTION

@app.post("/api/test/encrypt-file")
async def test_encrypt_file(file: UploadFile = File(...)):
    """
    Test endpoint to encrypt an uploaded file.
    Returns the encrypted filename which can be used to download the file later.
    """
    try:
        # Read the file content
        file_content = await file.read()
        
        # Generate AES key
        aes_key = generate_aes_key()
        
        # Encrypt the file
        encrypted_package = encrypt_file_with_aes(file_content, aes_key)
        
        # Generate a unique filename for the encrypted file
        original_filename = file.filename
        file_ext = os.path.splitext(original_filename)[1]
        encrypted_filename = f"encrypted_{generate_secret_key(16)}{file_ext}"
        encrypted_filepath = os.path.join(encrypted_files_dir, encrypted_filename)
        
        # Save the encrypted data to disk
        with open(encrypted_filepath, "wb") as f:
            f.write(encrypted_package['encrypted_data'])
        
        # Store encryption metadata for later decryption
        encryption_keys[encrypted_filename] = {
            "aes_key": binascii.hexlify(aes_key).decode('utf-8'),
            "iv": binascii.hexlify(encrypted_package['iv']).decode('utf-8'),
            "tag": binascii.hexlify(encrypted_package['tag']).decode('utf-8'),
            "original_filename": original_filename,
            "file_hash": calculate_file_hash(file_content)
        }
        
        logger.info(f"File encrypted and saved as {encrypted_filename}")
        
        return JSONResponse(content={
            "status": "success",
            "encrypted_filename": encrypted_filename,
            "original_filename": original_filename,
            "message": "File encrypted successfully"
        })
            
    except Exception as e:
        logger.error(f"Error encrypting file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error encrypting file: {str(e)}")

@app.get("/api/test/decrypt-file/{filename}")
async def test_decrypt_file(filename: str):
    """
    Test endpoint to decrypt a previously encrypted file.
    Provide the encrypted filename to download the decrypted file.
    """
    try:
        # Check if the file exists
        encrypted_filepath = os.path.join(encrypted_files_dir, filename)
        if not os.path.exists(encrypted_filepath):
            raise HTTPException(status_code=404, detail="Encrypted file not found")
        
        # Check if we have the encryption keys
        if filename not in encryption_keys:
            raise HTTPException(status_code=404, detail="Encryption keys not found for this file")
        
        # Get the encryption metadata
        metadata = encryption_keys[filename]
        aes_key = binascii.unhexlify(metadata["aes_key"])
        iv = binascii.unhexlify(metadata["iv"])
        tag = binascii.unhexlify(metadata["tag"])
        original_filename = metadata.get("original_filename", "decrypted_file")
        
        # Read the encrypted file
        with open(encrypted_filepath, "rb") as f:
            encrypted_data = f.read()
        
        # Create the encrypted package
        encrypted_package = {
            'encrypted_data': encrypted_data,
            'iv': iv,
            'tag': tag
        }
        
        # Decrypt the file
        decrypted_data = decrypt_file_with_aes(encrypted_package, aes_key)
        
        # Calculate hash for integrity verification
        decrypted_hash = calculate_file_hash(decrypted_data)
        is_intact = decrypted_hash == metadata.get("file_hash")
        
        if not is_intact:
            logger.warning(f"Integrity check failed for {filename}")
        
        # Create a temporary file for the decrypted content
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        decrypted_filepath = os.path.join(temp_dir, original_filename)
        with open(decrypted_filepath, "wb") as f:
            f.write(decrypted_data)
        
        logger.info(f"File {filename} decrypted successfully")
        
        # Return the file as an attachment for download
        return FileResponse(
            path=decrypted_filepath, 
            filename=original_filename,
            media_type="application/octet-stream"
        )
            
    except Exception as e:
        logger.error(f"Error decrypting file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error decrypting file: {str(e)}")

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
