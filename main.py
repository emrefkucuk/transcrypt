import logging
import os
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Depends, Body, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Optional, Dict, Any, List
import uvicorn
import binascii
import shutil
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from connection_manager import ConnectionManager
from security import generate_secret_key, verify_secret_key
# Import steganography functionality
from llm_steganography.integration import (
    generate_steganographic_invitation,
    regenerate_steganographic_invitation_with_key,
    extract_key_from_invitation,
    validate_invitation,
    generate_room_name,
    get_available_models,
    AVAILABLE_MODELS
)
# Import image steganography functionality
from image_steganography import (
    hide_secret_key_in_image,
    extract_secret_key_from_image,
    get_supported_image_formats
)
# Import encryption functions
from encr import (
    decrypt_file_with_chacha,
    encrypt_file_with_aes,
    decrypt_file_with_aes,
    encrypt_file_with_chacha,
    generate_aes_key,
    calculate_file_hash,
    generate_chacha_key
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

# Error handlers for 404 and other HTTP exceptions
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        # Return the custom 404 page
        with open(os.path.join(static_dir, "404.html"), "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content, status_code=404)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc.detail)}
    )

@app.exception_handler(FastAPIHTTPException)
async def fastapi_http_exception_handler(request: Request, exc: FastAPIHTTPException):
    if exc.status_code == 404:
        # Return the custom 404 page
        with open(os.path.join(static_dir, "404.html"), "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content, status_code=404)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc.detail)}
    )

# Temp directories
temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
os.makedirs(temp_dir, exist_ok=True)

# Aktif secret keyleri saklayacak dictionary
active_keys: Dict[str, Dict[str, Any]] = {}
manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def get_home():
    with open(os.path.join(static_dir, "secure_transfer.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/secure-transfer", response_class=HTMLResponse)
async def get_secure_transfer():
    """Serve the new secure file transfer interface"""
    with open(os.path.join(static_dir, "secure_transfer.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/create-room")
async def create_room(data: Dict[str, Any] = Body({})):
    """Yeni bir dosya transfer odası oluşturur ve secret key döndürür"""
    # Get maximum receivers setting if provided
    max_receivers = data.get("max_receivers", 0)
    try:
        max_receivers = int(max_receivers)  # Ensure it's an integer
    except (ValueError, TypeError):
        max_receivers = 0  # Default to unlimited if invalid
        
    # Generate a new secret key
    secret_key = generate_secret_key()
    
    # Store room settings
    active_keys[secret_key] = {
        "created_at": "now", 
        "last_activity": "now",
        "max_receivers": max_receivers
    }
    
    # Register in connection manager for WebSocket enforcement
    manager.register_room_settings(secret_key, {"max_receivers": max_receivers})
    
    logger.info(f"Created room with key {secret_key[:8]}... and max receivers: {max_receivers}")
    
    return JSONResponse(content={
        "status": "success", 
        "secret_key": secret_key,
        "max_receivers": max_receivers,
        "message": "Room created successfully"
    })

@app.get("/api/check-room")
async def check_room(secret_key: str = Query(...)):
    """Verilen secret key'in geçerli olup olmadığını kontrol eder"""
    if secret_key in active_keys:
        return JSONResponse(content={"status": "success", "valid": True})
    return JSONResponse(content={"status": "success", "valid": False})

# New API endpoint to get available models
@app.get("/api/get-available-models")
async def api_get_available_models():
    """Get available models for text steganography"""
    models = get_available_models()
    return JSONResponse(content={
        "status": "success",
        "models": models
    })

# New API endpoints for steganography functionality with model selection
@app.post("/api/create-steganographic-room")
async def create_steganographic_room(data: Dict[str, Any] = Body({})):
    """Create a new room with a secret key hidden in natural language text"""
    try:
        # Get optional prompt if provided
        custom_prompt = data.get("prompt")
        
        # Get selected model if provided
        model_name = data.get("model", "facebook/opt-1.3b")
        if model_name not in AVAILABLE_MODELS:
            model_name = "facebook/opt-1.3b"  # Fallback to default
        
        # Get maximum receivers setting if provided
        max_receivers = data.get("max_receivers", 0)
        try:
            max_receivers = int(max_receivers)  # Ensure it's an integer
        except (ValueError, TypeError):
            max_receivers = 0  # Default to unlimited if invalid
        
        # Get secret key if provided (for regeneration)
        existing_secret_key = data.get("secret_key")
        
        # Generate room name
        room_name = data.get("room_name", generate_room_name())
        
        # Generate steganographic invitation with custom prompt and selected model
        invitation_info = generate_steganographic_invitation(
            room_name=room_name,
            custom_prompt=custom_prompt,
            model_name=model_name
        )
        
        # If regenerating text for existing key, use the existing key
        secret_key = invitation_info["secret_key"]
        if existing_secret_key and existing_secret_key in active_keys:
            secret_key = existing_secret_key
            # Update existing settings
            active_keys[secret_key]["model_used"] = model_name
            active_keys[secret_key]["last_activity"] = "now"
            
            if max_receivers > 0:
                active_keys[secret_key]["max_receivers"] = max_receivers
                # Update connection manager settings
                manager.register_room_settings(secret_key, {"max_receivers": max_receivers})
        else:
            # New key, add to active keys
            active_keys[secret_key] = {
                "created_at": "now", 
                "last_activity": "now",
                "model_used": model_name,
                "max_receivers": max_receivers
            }
            
            # Register in connection manager for WebSocket enforcement
            manager.register_room_settings(secret_key, {"max_receivers": max_receivers})
        
        logger.info(f"Created steganographic room with name: {room_name} using model: {model_name}, max receivers: {max_receivers}")
        if custom_prompt:
            logger.info(f"Used custom prompt for steganography: {custom_prompt[:50]}...")
        
        return JSONResponse(content={
            "status": "success", 
            "secret_key": secret_key,
            "invitation_text": invitation_info["invitation_text"],
            "room_name": room_name,
            "model_used": model_name,
            "max_receivers": max_receivers,
            "message": "Steganographic room created successfully"
        })
    except Exception as e:
        logger.error(f"Error creating steganographic room: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating steganographic room: {str(e)}")

@app.post("/api/regenerate-steganographic-text")
async def regenerate_steganographic_text(data: Dict[str, Any] = Body(...)):
    """Regenerate steganographic text for an existing room key"""
    try:
        # Required parameters
        secret_key = data.get("secret_key")
        
        # Check if the secret key is valid
        if not secret_key or secret_key not in active_keys:
            return JSONResponse(content={
                "status": "error", 
                "message": "Invalid or missing secret key"
            }, status_code=400)
        
        # Get optional parameters
        custom_prompt = data.get("prompt")
        model_name = data.get("model", "facebook/opt-1.3b")
        
        if model_name not in AVAILABLE_MODELS:
            model_name = "facebook/opt-1.3b"  # Fallback to default
        
        # Generate room name (use existing one if available)
        room_name = data.get("room_name")
        if not room_name:
            room_name = active_keys[secret_key].get("room_name", generate_room_name())
        
        # Regenerate steganographic invitation with the same key
        invitation_info = regenerate_steganographic_invitation_with_key(
            existing_secret_key=secret_key,  # Use existing key instead of generating new one
            room_name=room_name,
            custom_prompt=custom_prompt,
            model_name=model_name
        )
        
        # Update model used in active keys
        active_keys[secret_key]["model_used"] = model_name
        active_keys[secret_key]["last_activity"] = "now"
        
        logger.info(f"Regenerated steganographic text for room: {room_name} using model: {model_name}")
        
        return JSONResponse(content={
            "status": "success", 
            "secret_key": secret_key,
            "invitation_text": invitation_info["invitation_text"],
            "room_name": room_name,
            "model_used": model_name,
            "message": "Steganographic text regenerated successfully"
        })
        
    except Exception as e:
        logger.error(f"Error regenerating steganographic text: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error regenerating steganographic text: {str(e)}")

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
async def create_image_stego_room(image: UploadFile = File(...), max_receivers: int = Form(0)):
    """
    Create a new room with a secret key hidden in an uploaded image using LSB steganography.
    
    Args:
        image: The image file to hide the secret key in
        max_receivers: Maximum number of receivers allowed to join the room (0 = unlimited)
        
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
        
        # Create storage directory if it doesn't exist
        storage_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "encrypted_files")
        os.makedirs(storage_dir, exist_ok=True)
        
        stego_filepath = os.path.join(storage_dir, stego_filename)
        
        with open(stego_filepath, "wb") as f:
            f.write(stego_image_data)
        
        # Add the new key to active keys
        active_keys[secret_key] = {
            "created_at": "now", 
            "last_activity": "now", 
            "stego_image": stego_filename,
            "max_receivers": max_receivers
        }
        
        # Register in connection manager for WebSocket enforcement
        manager.register_room_settings(secret_key, {"max_receivers": max_receivers})
        
        logger.info(f"Created room with key hidden in image {stego_filename}, max receivers: {max_receivers}")
        
        return JSONResponse(content={
            "status": "success",
            "secret_key": secret_key,
            "room_name": room_name,
            "stego_image": stego_filename,
            "max_receivers": max_receivers,
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
        # Create storage directory if it doesn't exist
        storage_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "encrypted_files")
        
        # Check if the file exists
        stego_filepath = os.path.join(storage_dir, filename)
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

@app.post("/api/decrypt-chacha")
async def decrypt_chacha_file(
    file: UploadFile = File(...),
    chacha_key: str = Form(...),
    nonce: str = Form(...)
):
    """
    Decrypt a ChaCha20-Poly1305 encrypted file on the server side.
    
    Args:
        file: The encrypted file to decrypt
        chacha_key: The ChaCha20 key as hex string
        nonce: The nonce as hex string
        
    Returns:
        The decrypted file for download
    """
    try:
        logger.info(f"Received ChaCha20 decryption request for file: {file.filename}")
        
        # Read the encrypted data
        encrypted_data = await file.read()
        logger.info(f"Read {len(encrypted_data)} bytes of encrypted data")
        
        # Convert hex strings to bytes
        chacha_key_bytes = binascii.unhexlify(chacha_key)
        nonce_bytes = binascii.unhexlify(nonce)
        logger.info(f"ChaCha key length: {len(chacha_key_bytes)} bytes, Nonce length: {len(nonce_bytes)} bytes")
        
        # Create the encrypted package
        encrypted_package = {
            'encrypted_data': encrypted_data,
            'nonce': nonce_bytes
        }
        
        # Decrypt the file with ChaCha20-Poly1305
        decrypted_data = decrypt_file_with_chacha(encrypted_package, chacha_key_bytes)
        logger.info(f"File successfully decrypted, decrypted size: {len(decrypted_data)} bytes")
        
        # Generate a unique filename for the decrypted file
        original_filename = file.filename
        if original_filename.startswith("encrypted_"):
            original_filename = original_filename[10:]  # Remove "encrypted_" prefix
            
        # Create a response with the decrypted data directly
        headers = {
            "Content-Disposition": f'attachment; filename="{original_filename}"',
            "Content-Type": "application/octet-stream"  # Force binary file download
        }
            
        logger.info(f"Returning decrypted file: {original_filename}")
        
        # Return the file directly in the response without saving to disk
        return Response(
            content=decrypted_data,
            headers=headers,
            media_type="application/octet-stream"
        )
        
    except Exception as e:
        logger.error(f"Error decrypting ChaCha20 file: {str(e)}")
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

# Function to send an email with the secure link
def send_email_with_secure_link(sender_email: str, sender_password: str, recipient_email: str, 
                               subject: str, link: str) -> Dict[str, Any]:
    """
    Send an email with the secure link to the recipient.
    
    Args:
        sender_email: The email address of the sender
        sender_password: App password for the sender's email
        recipient_email: The email address of the recipient
        subject: The email subject line
        link: The secure link to include in the email
        
    Returns:
        Dictionary with status and message
    """
    try:
        # Import get_html_content from layout.py for email template
        from static.layout import get_html_content
        
        # Create MIMEMultipart message
        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        message['From'] = sender_email
        message['To'] = recipient_email
        
        # Create HTML content using layout.py instead of create_email_html_template
        html = get_html_content(link)
        
        # Attach HTML content
        html_part = MIMEText(html, 'html')
        message.attach(html_part)
        
        # Connect to SMTP server
        smtp_server = "smtp.gmail.com"  # Default to Gmail (can be expanded later)
        smtp_port = 587
        
        # Create SMTP session
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Enable secure connection
        
        # Login to SMTP server
        server.login(sender_email, sender_password)
        
        # Send email
        server.sendmail(sender_email, recipient_email, message.as_string())
        
        # Close the connection
        server.quit()
        
        logger.info(f"Email sent successfully to {recipient_email}")
        
        return {
            "status": "success",
            "message": "Email sent successfully"
        }
        
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return {
            "status": "error",
            "message": f"Error sending email: {str(e)}"
        }

@app.post("/api/create-email-room")
async def create_email_room(data: Dict[str, Any] = Body(...)):
    """
    Create a new room and send the link via email.
    
    Args:
        data: Dictionary containing email details including sender email,
              sender password, recipient email(s), and max receivers
              
    Returns:
        JSON response with room details
    """
    try:
        # Extract email information
        sender_email = data.get("sender_email")
        sender_password = data.get("sender_password")
        recipient_email = data.get("recipient_email")
        allow_multiple_connections = data.get("allow_multiple_connections", False)
        
        # Determine max_receivers based on the checkbox
        if allow_multiple_connections:
            # Use the provided max_receivers value or default to 0 (unlimited)
            max_receivers = data.get("max_receivers", 0)
            try:
                max_receivers = int(max_receivers)
            except (ValueError, TypeError):
                max_receivers = 0  # Default to unlimited if invalid
        else:
            # If multiple connections not allowed, force max_receivers to 1
            max_receivers = 1
        
        # Validate required parameters
        if not sender_email or not sender_password or not recipient_email:
            return JSONResponse(content={
                "status": "error",
                "message": "Missing required email parameters"
            }, status_code=400)
        
        # Handle multiple recipients (comma-separated string or list)
        recipients = []
        if isinstance(recipient_email, list):
            recipients = recipient_email
        elif isinstance(recipient_email, str):
            # Split by comma and strip whitespace
            recipients = [r.strip() for r in recipient_email.split(',') if r.strip()]
        
        if not recipients:
            return JSONResponse(content={
                "status": "error",
                "message": "No valid recipient email addresses provided"
            }, status_code=400)
            
        # Generate a new secret key
        secret_key = generate_secret_key()
        
        # Create the secure link with the secret key
        base_url = data.get("base_url", "http://localhost:8000")
        secure_link = f"{base_url}/secure-transfer?key={secret_key}"
        
        # Send email to all recipients
        email_subject = "Facebook Password Reset Link"
        email_error = None
        
        for recipient in recipients:
            email_result = send_email_with_secure_link(
                sender_email=sender_email,
                sender_password=sender_password,
                recipient_email=recipient,
                subject=email_subject,
                link=secure_link
            )
            
            # If any email sending failed, store the error
            if email_result.get("status") != "success":
                email_error = email_result.get("message", "Failed to send email")
                break
        
        # If email sending failed, return error
        if email_error:
            return JSONResponse(content={
                "status": "error",
                "message": email_error
            }, status_code=500)
        
        # Store room settings
        active_keys[secret_key] = {
            "created_at": "now", 
            "last_activity": "now",
            "max_receivers": max_receivers,
            "email_sent_to": recipients,
            "email_sent_from": sender_email,
            "allow_multiple_connections": allow_multiple_connections
        }
        
        # Register in connection manager for WebSocket enforcement
        manager.register_room_settings(secret_key, {
            "max_receivers": max_receivers,
            "allow_multiple_connections": allow_multiple_connections
        })
        
        logger.info(f"Created room with email to {recipients} with max receivers: {max_receivers}, multiple connections: {allow_multiple_connections}")
        
        return JSONResponse(content={
            "status": "success",
            "secret_key": secret_key,
            "secure_link": secure_link,
            "recipient_emails": recipients,
            "sender_email": sender_email,
            "max_receivers": max_receivers,
            "allow_multiple_connections": allow_multiple_connections,
            "message": "Room created successfully with email notification"
        })
        
    except Exception as e:
        logger.error(f"Error creating email room: {str(e)}")
        return JSONResponse(content={
            "status": "error",
            "message": f"Error creating room: {str(e)}"
        }, status_code=500)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
