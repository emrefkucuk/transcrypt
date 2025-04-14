"""
LLM Steganography core functions.

This module provides functions to encode and decode secret keys in LLM-generated text.
"""

import base64
import json
import re
import random
import sys
import os
import binascii
from typing import Tuple, Optional, Dict, List, Any
import numpy as np

# Add parent directory to sys.path to import from security.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from security import generate_secret_key, verify_secret_key

# Fix imports to use absolute paths instead of relative
from llm_steganography.mec import MinimumEntropyCoupler
from llm_steganography.utils import text_to_bits, bits_to_text, get_text_statistics, modify_text_statistics
from llm_steganography.text_generation import generate_text, predict_next_token_distribution


# Initialize the MEC coupler
coupler = MinimumEntropyCoupler()


def encode_secret_in_text(secret_key: str, cover_text: str) -> str:
    """
    Encode a secret key into a piece of text using MEC.
    
    Args:
        secret_key: The secret key to hide
        cover_text: The text to hide the secret key in
        
    Returns:
        The stegotext containing the hidden secret key
    """
    # Get cover text statistics
    cover_stats = get_text_statistics(cover_text)
    
    # Convert text to list of words for processing
    words = cover_text.split()
    stegotext_words = []
    
    # Store words that were used for encoding (for debugging)
    encoded_positions = []
    
    # Process some words to embed a few bits as a "canary" value
    # This helps validate our extraction algorithm
    canary_bits = [1, 0, 1, 0]  # Simple pattern
    bits_encoded = 0
    
    for i, word in enumerate(words):
        if bits_encoded >= len(canary_bits):
            # All canary bits encoded, add remaining words unchanged
            stegotext_words.extend(words[i:])
            break
            
        # For each word, decide if we'll use it for encoding
        if len(word) >= 4 and bits_encoded < len(canary_bits):
            # Get next bit to encode
            bit = canary_bits[bits_encoded]
            
            # Apply subtle modification to encode the bit
            if bit == 1:
                # For bit 1: capitalize first letter if not already capitalized
                if word[0].islower() and not (i == 0 or (i > 0 and words[i-1].endswith(('.', '!', '?')))):
                    word = word[0].upper() + word[1:]
                    encoded_positions.append((i, 1))
                    bits_encoded += 1
            else:
                # For bit 0: ensure first letter is lowercase if not start of sentence
                if word[0].isupper() and not (i == 0 or (i > 0 and words[i-1].endswith(('.', '!', '?')))):
                    word = word[0].lower() + word[1:]
                    encoded_positions.append((i, 0))
                    bits_encoded += 1
        
        stegotext_words.append(word)
    
    # Encode the secret key using invisible Unicode characters
    # Convert to base64 first
    key_b64 = base64.urlsafe_b64encode(secret_key.encode('utf-8')).decode('utf-8')
    
    # Define invisible character mapping
    # We'll use zero-width characters to encode base64 alphabet
    char_map = {
        # Map base64 characters to combinations of zero-width characters
        'A': '\u200B\u200B\u200B', 'B': '\u200B\u200B\u200C', 'C': '\u200B\u200B\u200D',
        'D': '\u200B\u200C\u200B', 'E': '\u200B\u200C\u200C', 'F': '\u200B\u200C\u200D',
        'G': '\u200B\u200D\u200B', 'H': '\u200B\u200D\u200C', 'I': '\u200B\u200D\u200D',
        'J': '\u200C\u200B\u200B', 'K': '\u200C\u200B\u200C', 'L': '\u200C\u200B\u200D',
        'M': '\u200C\u200C\u200B', 'N': '\u200C\u200C\u200C', 'O': '\u200C\u200C\u200D',
        'P': '\u200C\u200D\u200B', 'Q': '\u200C\u200D\u200C', 'R': '\u200C\u200D\u200D',
        'S': '\u200D\u200B\u200B', 'T': '\u200D\u200B\u200C', 'U': '\u200D\u200B\u200D',
        'V': '\u200D\u200C\u200B', 'W': '\u200D\u200C\u200C', 'X': '\u200D\u200C\u200D',
        'Y': '\u200D\u200D\u200B', 'Z': '\u200D\u200D\u200C', 'a': '\u200D\u200D\u200D',
        'b': '\u200B\u200B\u200E', 'c': '\u200B\u200C\u200E', 'd': '\u200B\u200D\u200E',
        'e': '\u200C\u200B\u200E', 'f': '\u200C\u200C\u200E', 'g': '\u200C\u200D\u200E',
        'h': '\u200D\u200B\u200E', 'i': '\u200D\u200C\u200E', 'j': '\u200D\u200D\u200E',
        'k': '\u200B\u200E\u200B', 'l': '\u200B\u200E\u200C', 'm': '\u200B\u200E\u200D',
        'n': '\u200C\u200E\u200B', 'o': '\u200C\u200E\u200C', 'p': '\u200C\u200E\u200D',
        'q': '\u200D\u200E\u200B', 'r': '\u200D\u200E\u200C', 's': '\u200D\u200E\u200D',
        't': '\u200E\u200B\u200B', 'u': '\u200E\u200B\u200C', 'v': '\u200E\u200B\u200D',
        'w': '\u200E\u200C\u200B', 'x': '\u200E\u200C\u200C', 'y': '\u200E\u200C\u200D',
        'z': '\u200E\u200D\u200B', '0': '\u200E\u200D\u200C', '1': '\u200E\u200D\u200D',
        '2': '\u200E\u200E\u200B', '3': '\u200E\u200E\u200C', '4': '\u200E\u200E\u200D',
        '5': '\u200F\u200B\u200B', '6': '\u200F\u200B\u200C', '7': '\u200F\u200B\u200D',
        '8': '\u200F\u200C\u200B', '9': '\u200F\u200C\u200C', '+': '\u200F\u200C\u200D',
        '/': '\u200F\u200D\u200B', '_': '\u200F\u200D\u200C', '-': '\u200F\u200D\u200D',
        '=': '\u200F\u200E\u200B'
    }
    
    # Start marker for invisible key
    invisible_marker = '\u200B\u200C\u200D\u200E\u200F'
    
    # End marker
    invisible_end_marker = '\u200F\u200E\u200D\u200C\u200B'
    
    # Convert base64 key to invisible characters
    invisible_key = invisible_marker
    for char in key_b64:
        if char in char_map:
            invisible_key += char_map[char]
    invisible_key += invisible_end_marker
    
    # Append the invisible key to the text - it will be completely invisible
    stegotext = ' '.join(stegotext_words) + invisible_key
    
    # Add a subtle marker at the beginning
    marker = '\u200B\u200C\u200B\u200C'  # Alternating zero-width space and zero-width non-joiner
    stegotext = marker + stegotext
    
    # Print debug info
    print(f"Debug - Encoded {bits_encoded} canary bits in text")
    print(f"Debug - Used {len(encoded_positions)} words for bit encoding")
    print(f"Debug - Invisibly embedded key has {len(key_b64)} characters")
    
    return stegotext


def decode_secret_from_text(stegotext: str) -> Optional[str]:
    """
    Extract a secret key from stegotext.
    
    Args:
        stegotext: Text potentially containing a hidden secret key
        
    Returns:
        The extracted secret key if found, None otherwise
    """
    # Check for the marker that indicates hidden data
    marker = '\u200B\u200C\u200B\u200C'  # Alternating zero-width space and zero-width non-joiner
    if not stegotext.startswith(marker):
        print("Debug - No marker found at start of text")
        # Try with the old marker format as fallback
        old_marker = '\u200B\u200B\u200C\u200B'
        if not stegotext.startswith(old_marker):
            return None
        else:
            marker = old_marker
            print("Debug - Found old marker format")
    
    # Remove marker from start
    text = stegotext[len(marker):]
    
    # Define invisible character mapping (reverse of encoding map)
    invisible_chars = {
        # Zero-width character combinations to base64 characters
        '\u200B\u200B\u200B': 'A', '\u200B\u200B\u200C': 'B', '\u200B\u200B\u200D': 'C',
        '\u200B\u200C\u200B': 'D', '\u200B\u200C\u200C': 'E', '\u200B\u200C\u200D': 'F',
        '\u200B\u200D\u200B': 'G', '\u200B\u200D\u200C': 'H', '\u200B\u200D\u200D': 'I',
        '\u200C\u200B\u200B': 'J', '\u200C\u200B\u200C': 'K', '\u200C\u200B\u200D': 'L',
        '\u200C\u200C\u200B': 'M', '\u200C\u200C\u200C': 'N', '\u200C\u200C\u200D': 'O',
        '\u200C\u200D\u200B': 'P', '\u200C\u200D\u200C': 'Q', '\u200C\u200D\u200D': 'R',
        '\u200D\u200B\u200B': 'S', '\u200D\u200B\u200C': 'T', '\u200D\u200B\u200D': 'U',
        '\u200D\u200C\u200B': 'V', '\u200D\u200C\u200C': 'W', '\u200D\u200C\u200D': 'X',
        '\u200D\u200D\u200B': 'Y', '\u200D\u200D\u200C': 'Z', '\u200D\u200D\u200D': 'a',
        '\u200B\u200B\u200E': 'b', '\u200B\u200C\u200E': 'c', '\u200B\u200D\u200E': 'd',
        '\u200C\u200B\u200E': 'e', '\u200C\u200C\u200E': 'f', '\u200C\u200D\u200E': 'g',
        '\u200D\u200B\u200E': 'h', '\u200D\u200C\u200E': 'i', '\u200D\u200D\u200E': 'j',
        '\u200B\u200E\u200B': 'k', '\u200B\u200E\u200C': 'l', '\u200B\u200E\u200D': 'm',
        '\u200C\u200E\u200B': 'n', '\u200C\u200E\u200C': 'o', '\u200C\u200E\u200D': 'p',
        '\u200D\u200E\u200B': 'q', '\u200D\u200E\u200C': 'r', '\u200D\u200E\u200D': 's',
        '\u200E\u200B\u200B': 't', '\u200E\u200B\u200C': 'u', '\u200E\u200B\u200D': 'v',
        '\u200E\u200C\u200B': 'w', '\u200E\u200C\u200C': 'x', '\u200E\u200C\u200D': 'y',
        '\u200E\u200D\u200B': 'z', '\u200E\u200D\u200C': '0', '\u200E\u200D\u200D': '1',
        '\u200E\u200E\u200B': '2', '\u200E\u200E\u200C': '3', '\u200E\u200E\u200D': '4',
        '\u200F\u200B\u200B': '5', '\u200F\u200B\u200C': '6', '\u200F\u200B\u200D': '7',
        '\u200F\u200C\u200B': '8', '\u200F\u200C\u200C': '9', '\u200F\u200C\u200D': '+',
        '\u200F\u200D\u200B': '/', '\u200F\u200D\u200C': '_', '\u200F\u200D\u200D': '-',
        '\u200F\u200E\u200B': '='
    }
    
    # Start marker for invisible key
    invisible_marker = '\u200B\u200C\u200D\u200E\u200F'
    
    # End marker
    invisible_end_marker = '\u200F\u200E\u200D\u200C\u200B'
    
    # Look for the invisible key
    marker_pos = text.find(invisible_marker)
    if marker_pos >= 0:
        # Find end marker
        end_pos = text.find(invisible_end_marker, marker_pos)
        if end_pos > marker_pos:
            # Extract the invisible text between markers
            invisible_text = text[marker_pos + len(invisible_marker):end_pos]
            
            # Decode the invisible characters back to base64
            base64_chars = []
            i = 0
            while i < len(invisible_text):
                # Try to match chunks of 3 zero-width characters
                if i + 3 <= len(invisible_text):
                    chunk = invisible_text[i:i+3]
                    if chunk in invisible_chars:
                        base64_chars.append(invisible_chars[chunk])
                        i += 3
                    else:
                        i += 1
                else:
                    i += 1
            
            base64_str = ''.join(base64_chars)
            
            try:
                # Decode base64 back to the original key
                key_bytes = base64.urlsafe_b64decode(base64_str)
                key_text = key_bytes.decode('utf-8')
                print(f"Debug - Successfully extracted key using invisible characters")
                return key_text
            except Exception as e:
                print(f"Debug - Error decoding invisible key: {e}")
    
    # Fall back to checking for direct base64 encoded key (old format with KEY prefix)
    key_pattern = r'KEY([A-Za-z0-9_-]+={0,2})'
    key_match = re.search(key_pattern, text)
    
    if key_match:
        try:
            # Try to decode the base64 key directly
            key_base64 = key_match.group(1)
            key_bytes = base64.urlsafe_b64decode(key_base64)
            key_text = key_bytes.decode('utf-8')
            print(f"Debug - Successfully extracted key using direct base64 method")
            return key_text
        except Exception as e:
            print(f"Debug - Error decoding direct base64 key: {e}")
    
    # If we can't find a valid key, indicate failure
    print("Debug - Could not extract a valid key from the text")
    return None


def generate_cover_text_with_secret(prompt: str, secret_key: str, max_length: int = 500) -> str:
    """
    Generate cover text using an LLM and embed a secret key.
    
    Args:
        prompt: The prompt to give the LLM
        secret_key: The secret key to hide
        max_length: Maximum length of generated text
        
    Returns:
        LLM-generated text with the secret key embedded
    """
    # Generate cover text using LLM
    cover_text = generate_text(prompt, max_length)
    
    # Encode the secret key into the cover text
    stegotext = encode_secret_in_text(secret_key, cover_text)
    
    return stegotext


def verify_extracted_key(extracted_key: str, stored_key: str) -> bool:
    """
    Verify if an extracted key matches the stored key.
    
    Args:
        extracted_key: Key extracted from stegotext
        stored_key: Original key to compare against
        
    Returns:
        True if keys match, False otherwise
    """
    if extracted_key is None:
        return False
    return verify_secret_key(extracted_key, stored_key)


def generate_and_verify_stegotext(prompt: str) -> Tuple[str, str, str]:
    """
    Generate a secret key, create stegotext, and verify extraction.
    
    Args:
        prompt: The prompt for text generation
        
    Returns:
        Tuple of (secret_key, stegotext, extracted_key)
    """
    # Generate a new secret key
    secret_key = generate_secret_key()
    
    # Generate cover text with embedded secret
    stegotext = generate_cover_text_with_secret(prompt, secret_key)
    
    # Extract the secret to verify it worked
    extracted_key = decode_secret_from_text(stegotext)
    
    return secret_key, stegotext, extracted_key
