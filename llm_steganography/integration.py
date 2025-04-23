"""
Integration module for LLM steganography with the main encryption API.

This module provides functions to integrate the steganography capabilities
with the main application's secret key management.
"""

import os
import sys
import json
from typing import Dict, Any, Optional, Tuple

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from security import generate_secret_key, verify_secret_key
from llm_steganography.steganography import (
    encode_secret_in_text,
    decode_secret_from_text,
    generate_cover_text_with_secret
)
from llm_steganography.text_generation import generate_text, load_model

# Define available models for selection
AVAILABLE_MODELS = [
    "facebook/opt-1.3b",
    "EleutherAI/pythia-1b",
    "microsoft/phi-1_5",
    "gpt2"
]

def get_available_models() -> Dict[str, str]:
    """
    Get available models for text generation with user-friendly names.
    
    Returns:
        Dictionary of model_id: display_name pairs
    """
    return {
        "facebook/opt-1.3b": "Meta OPT (1.3B)",
        "EleutherAI/pythia-1b": "Pythia (1B)",
        "microsoft/phi-1_5": "Microsoft Phi-1.5",
        "gpt2": "OpenAI GPT-2"
    }

def generate_steganographic_invitation(
    room_name: Optional[str] = None, 
    custom_prompt: Optional[str] = None,
    model_name: str = "facebook/opt-1.3b"
) -> Dict[str, Any]:
    """
    Generate a room invitation with a secret key hidden in natural text.
    
    Args:
        room_name: Optional name for the room
        custom_prompt: Optional custom prompt for text generation
        model_name: Name of the model to use for text generation
        
    Returns:
        Dictionary containing invitation text and metadata
    """
    # Generate a new secret key
    secret_key = generate_secret_key()
    
    # Always use custom prompt if provided
    if custom_prompt:
        prompt = custom_prompt
    else:
        # Default prompt if none provided
        prompt = "Write a short message explaining secure file sharing benefits."
    
    # Load the selected model
    if model_name in AVAILABLE_MODELS:
        load_model(model_name)
    
    # Generate cover text with embedded secret
    invitation_text = generate_cover_text_with_secret(prompt, secret_key)
    
    return {
        "invitation_text": invitation_text,
        "secret_key": secret_key,
        "has_hidden_key": True,
        "model_used": model_name
    }


def extract_key_from_invitation(invitation_text: str) -> Optional[str]:
    """
    Extract a secret key from an invitation text.
    
    Args:
        invitation_text: The invitation text
        
    Returns:
        The extracted secret key if found, None otherwise
    """
    return decode_secret_from_text(invitation_text)


def validate_invitation(invitation_text: str, expected_key: str) -> bool:
    """
    Validate if an invitation has the expected secret key.
    
    Args:
        invitation_text: The invitation text
        expected_key: The expected secret key
        
    Returns:
        True if the invitation contains the expected key, False otherwise
    """
    extracted_key = extract_key_from_invitation(invitation_text)
    if not extracted_key:
        return False
    
    return verify_secret_key(extracted_key, expected_key)


def create_room_with_steganographic_key(
    custom_prompt: Optional[str] = None,
    model_name: str = "facebook/opt-1.3b"
) -> Dict[str, Any]:
    """
    Create a new room with a steganographically hidden key.
    
    Args:
        custom_prompt: Optional custom prompt for text generation
        model_name: Name of the model to use for text generation
        
    Returns:
        Dictionary with room information including invitation text
    """
    invitation_info = generate_steganographic_invitation(
        custom_prompt=custom_prompt,
        model_name=model_name
    )
    
    return {
        "status": "success",
        "message": "Room created with steganographic key",
        "secret_key": invitation_info["secret_key"],
        "invitation_text": invitation_info["invitation_text"],
        "model_used": model_name
    }


def join_room_with_invitation(invitation_text: str) -> Dict[str, Any]:
    """
    Join a room using an invitation containing a hidden secret key.
    
    Args:
        invitation_text: The invitation text containing a hidden key
        
    Returns:
        Dictionary with join status and extracted key if successful
    """
    extracted_key = extract_key_from_invitation(invitation_text)
    
    if not extracted_key:
        return {
            "status": "error",
            "message": "No valid secret key found in the invitation text"
        }
    
    return {
        "status": "success",
        "message": "Successfully extracted room key from invitation",
        "secret_key": extracted_key
    }


# API function to generate human-readable room names
def generate_room_name() -> str:
    """Generate a human-readable room name."""
    adjectives = ["Secure", "Private", "Encrypted", "Protected", "Confidential", 
                 "Hidden", "Secret", "Safe", "Trusted", "Quantum"]
    nouns = ["Vault", "Room", "Channel", "Transfer", "Exchange", "Space",
            "Portal", "Gateway", "Tunnel", "Nexus"]
    
    import random
    return f"{random.choice(adjectives)}{random.choice(nouns)}"
