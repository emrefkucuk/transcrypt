"""
Image Steganography module for hiding and extracting secret keys in images.

This module provides functions to hide and extract secret keys in/from images using
the LSB (Least Significant Bit) method. Implementation based on Helium-He/Image-Steganography.
"""

import os
import io
import base64
import logging
from PIL import Image
from typing import Dict, Any, List, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("image_steganography")


def str_to_bin(message: str) -> str:
    """
    Convert a string message to binary representation
    
    Args:
        message: The string message to convert
        
    Returns:
        Binary string representation
    """
    binary = ""
    for char in message:
        ascii_value = ord(char)
        # Convert to 8-bit binary and remove '0b' prefix
        binary_char = bin(ascii_value)[2:].zfill(8)
        binary += binary_char
    return binary


def bin_to_str(binary: str) -> str:
    """
    Convert binary string representation back to text
    
    Args:
        binary: Binary string representation
        
    Returns:
        Original string message
    """
    message = ""
    for i in range(0, len(binary), 8):
        # Take 8 bits at a time
        byte = binary[i:i+8]
        if len(byte) == 8:  # Ensure we have a full byte
            ascii_value = int(byte, 2)
            message += chr(ascii_value)
    return message


def hide_secret_key_in_image(image_data: bytes, secret_key: str) -> Dict[str, Any]:
    """
    Hide a secret key in an image using LSB steganography.
    
    Args:
        image_data: Binary data of the image
        secret_key: The secret key to hide
        
    Returns:
        Dictionary with status and steganographic image data if successful
    """
    try:
        # Load the image from bytes
        image_buffer = io.BytesIO(image_data)
        img = Image.open(image_buffer)
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Get pixel data
        pixels = list(img.getdata())
        width, height = img.size
        
        # Prepare the message (add marker for extraction validation)
        message = "STEGO_KEY:" + secret_key + ":END"
        
        # Convert message to binary
        binary_message = str_to_bin(message)
        message_length = len(binary_message)
        
        logger.info(f"Message to hide: {message}")
        logger.info(f"Binary length: {message_length} bits")
        
        # Check if the image is large enough
        if message_length > len(pixels) * 3:
            return {
                "status": "error",
                "message": f"Image too small to hide the message. Need at least {message_length // 3 + 1} pixels."
            }
        
        # First, embed the length of the binary message (32 bits)
        # This will help during extraction
        length_binary = bin(message_length)[2:].zfill(32)
        
        # New pixel list to store modified pixels
        new_pixels = []
        
        # Embed message length in the first 32 pixels (1 bit per color channel)
        bit_index = 0
        for i in range(11):  # First 11 pixels (33 bits: 32 for length + 1 for delimiter)
            r, g, b = pixels[i]
            
            if bit_index < 32:  # Embed length bits
                # Modify R channel
                r = r & ~1 | int(length_binary[bit_index])
                bit_index += 1
                
                if bit_index < 32:
                    # Modify G channel
                    g = g & ~1 | int(length_binary[bit_index])
                    bit_index += 1
                
                if bit_index < 32:
                    # Modify B channel
                    b = b & ~1 | int(length_binary[bit_index])
                    bit_index += 1
            else:
                # Add a delimiter bit (1) after length
                r = r & ~1 | 1
            
            new_pixels.append((r, g, b))
        
        # Embed the actual message
        bit_index = 0
        for i in range(11, len(pixels)):
            if bit_index >= message_length:
                # No more bits to embed, keep remaining pixels unchanged
                new_pixels.append(pixels[i])
                continue
            
            r, g, b = pixels[i]
            
            # Modify R channel
            if bit_index < message_length:
                r = r & ~1 | int(binary_message[bit_index])
                bit_index += 1
            
            # Modify G channel
            if bit_index < message_length:
                g = g & ~1 | int(binary_message[bit_index])
                bit_index += 1
            
            # Modify B channel
            if bit_index < message_length:
                b = b & ~1 | int(binary_message[bit_index])
                bit_index += 1
            
            new_pixels.append((r, g, b))
        
        # Add any remaining pixels unchanged
        if len(new_pixels) < len(pixels):
            new_pixels.extend(pixels[len(new_pixels):])
        
        # Create a new image with the modified pixels
        stego_img = Image.new(img.mode, (width, height))
        stego_img.putdata(new_pixels)
        
        # Save the image to bytes
        output_buffer = io.BytesIO()
        stego_img.save(output_buffer, format='PNG')
        stego_image_data = output_buffer.getvalue()
        
        logger.info(f"Successfully hidden secret key. Used {bit_index} out of {message_length} bits")
        
        return {
            "status": "success",
            "stego_image_data": stego_image_data
        }
        
    except Exception as e:
        logger.error(f"Error hiding secret key in image: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to hide secret key in image: {str(e)}"
        }


def extract_secret_key_from_image(image_data: bytes) -> Dict[str, Any]:
    """
    Extract a secret key from a steganographic image.
    
    Args:
        image_data: Binary data of the steganographic image
        
    Returns:
        Dictionary with status and extracted secret key if successful
    """
    try:
        # Load the image from bytes
        image_buffer = io.BytesIO(image_data)
        img = Image.open(image_buffer)
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Get pixel data
        pixels = list(img.getdata())
        
        # First, extract the message length (32 bits)
        length_binary = ""
        for i in range(11):  # First 11 pixels
            r, g, b = pixels[i]
            
            if len(length_binary) < 32:
                length_binary += str(r & 1)
            if len(length_binary) < 32:
                length_binary += str(g & 1)
            if len(length_binary) < 32:
                length_binary += str(b & 1)
        
        # Convert binary length to integer
        message_length = int(length_binary[:32], 2)
        
        logger.info(f"Extracted message length: {message_length} bits")
        
        # Extract the message bits
        binary_message = ""
        bit_count = 0
        
        for i in range(11, len(pixels)):
            if bit_count >= message_length:
                break
                
            r, g, b = pixels[i]
            
            # Extract from R channel
            if bit_count < message_length:
                binary_message += str(r & 1)
                bit_count += 1
            
            # Extract from G channel
            if bit_count < message_length:
                binary_message += str(g & 1)
                bit_count += 1
            
            # Extract from B channel
            if bit_count < message_length:
                binary_message += str(b & 1)
                bit_count += 1
        
        # Convert binary to string
        extracted_message = bin_to_str(binary_message)
        logger.info(f"Extracted raw message: {extracted_message[:50]}...")
        
        # Look for the marker and extract the key
        if "STEGO_KEY:" in extracted_message and ":END" in extracted_message:
            start_marker = "STEGO_KEY:"
            end_marker = ":END"
            start_pos = extracted_message.find(start_marker) + len(start_marker)
            end_pos = extracted_message.find(end_marker, start_pos)
            
            if start_pos >= len(start_marker) and end_pos > start_pos:
                secret_key = extracted_message[start_pos:end_pos]
                logger.info(f"Successfully extracted secret key: {secret_key}")
                
                return {
                    "status": "success",
                    "secret_key": secret_key
                }
        
        logger.warning("No valid steganographic marker found in the image")
        return {
            "status": "error",
            "message": "No secret key found in this image"
        }
        
    except Exception as e:
        logger.error(f"Error extracting secret key from image: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to extract secret key from image: {str(e)}"
        }


def get_supported_image_formats() -> List[str]:
    """
    Get a list of supported image formats for steganography.
    
    Returns:
        List of supported image formats
    """
    return ["PNG", "JPG", "JPEG", "BMP", "TIFF", "WEBP"]