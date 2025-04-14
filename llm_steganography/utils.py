"""
Utility functions for LLM steganography.

This module provides helper functions for text manipulation, bit conversion,
and statistical analysis needed for steganography operations.
"""

import base64
import re
import numpy as np
from typing import List, Dict, Any, Tuple


def text_to_bits(text: str) -> List[int]:
    """
    Convert text to a list of bits.
    
    Args:
        text: Text to convert
        
    Returns:
        List of bits (0s and 1s)
    """
    # Convert text to bytes
    bytes_data = text.encode('utf-8')
    
    # Convert bytes to bits - Use consistent MSB-first order for better reliability
    result = []
    for b in bytes_data:
        # Use MSB to LSB order
        for i in range(7, -1, -1):
            result.append((b >> i) & 1)
    
    return result


def bits_to_text(bits: List[int]) -> str:
    """
    Convert a list of bits back to text.
    
    Args:
        bits: List of bits (0s and 1s)
        
    Returns:
        Reconstructed text
    """
    # Ensure the number of bits is a multiple of 8
    padding_needed = (8 - len(bits) % 8) % 8
    padded_bits = bits + [0] * padding_needed
    
    # Convert bits to bytes - Use consistent MSB-first order
    byte_array = bytearray()
    for i in range(0, len(padded_bits), 8):
        byte = 0
        # Use MSB to LSB order
        for j in range(8):
            if i + j < len(padded_bits):
                byte = (byte << 1) | padded_bits[i + j]
        byte_array.append(byte)
    
    # Convert bytes to text
    try:
        # Attempt to decode the full byte array
        return byte_array.decode('utf-8')
    except UnicodeDecodeError:
        # Handle potential decoding errors by trying different lengths
        for length in range(len(byte_array), 0, -1):
            try:
                return byte_array[:length].decode('utf-8')
            except UnicodeDecodeError:
                continue
        
        # If all attempts failed, return a base64 representation
        return base64.b64encode(byte_array).decode('utf-8')


def get_text_statistics(text: str) -> Dict[str, Any]:
    """
    Calculate statistical properties of text for maintaining natural appearance.
    
    Args:
        text: The text to analyze
        
    Returns:
        Dictionary containing statistical measures
    """
    # Basic statistics to track
    stats = {
        'avg_sentence_length': 0,
        'avg_word_length': 0,
        'punctuation_freq': {},
        'letter_freq': {},
        'common_words': {}
    }
    
    # Count sentence lengths
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if sentences:
        total_sentences = len(sentences)
        sentence_lengths = [len(s.split()) for s in sentences]
        stats['avg_sentence_length'] = sum(sentence_lengths) / total_sentences
    
    # Count word lengths and frequencies
    words = re.findall(r'\b\w+\b', text.lower())
    if words:
        total_words = len(words)
        stats['avg_word_length'] = sum(len(word) for word in words) / total_words
        
        # Count word frequencies
        for word in words:
            if word in stats['common_words']:
                stats['common_words'][word] += 1
            else:
                stats['common_words'][word] = 1
    
    # Count punctuation
    for char in text:
        if char in '.,:;?!-()[]{}\'"/':
            if char in stats['punctuation_freq']:
                stats['punctuation_freq'][char] += 1
            else:
                stats['punctuation_freq'][char] = 1
    
    # Count letter frequencies
    for char in text.lower():
        if char.isalpha():
            if char in stats['letter_freq']:
                stats['letter_freq'][char] += 1
            else:
                stats['letter_freq'][char] = 1
    
    return stats


def modify_text_statistics(text: str, target_stats: Dict[str, Any]) -> str:
    """
    Subtly modify text to match target statistical properties.
    
    Args:
        text: Text to modify
        target_stats: Target statistical properties
        
    Returns:
        Modified text with statistical properties closer to target
    """
    # This implementation is simplified, just making minimal adjustments
    # to demonstrate the concept without significant text alteration
    
    # We'll focus on preserving the most important aspects
    # while ensuring our steganographic markers remain intact
    
    # For real implementation, more sophisticated language model-based 
    # adjustments would be needed
    
    return text


def binary_to_base64(binary_data: bytes) -> str:
    """
    Convert binary data to base64 string.
    
    Args:
        binary_data: Binary data to convert
        
    Returns:
        Base64-encoded string
    """
    return base64.b64encode(binary_data).decode('utf-8')


def base64_to_binary(base64_str: str) -> bytes:
    """
    Convert base64 string to binary data.
    
    Args:
        base64_str: Base64-encoded string
        
    Returns:
        Binary data
    """
    return base64.b64decode(base64_str)


def distribute_bits_naturally(text: str, bits: List[int]) -> str:
    """
    Distribute bits throughout text in a natural way.
    
    Args:
        text: Text to embed bits in
        bits: Bits to embed
        
    Returns:
        Modified text with embedded bits
    """
    words = text.split()
    result_words = []
    bit_index = 0
    
    for i, word in enumerate(words):
        if bit_index >= len(bits):
            # All bits embedded, add remaining words
            result_words.extend(words[i:])
            break
            
        # Only modify some words based on length and position
        if len(word) >= 4 and i % 3 == 0:
            # Use various natural text modifications to encode bits
            if bits[bit_index] == 1:
                # For bit 1: Various modifications
                if "'" not in word:
                    # Maybe add a contraction
                    if word.endswith('s'):
                        word = word[:-1] + "'s"
                else:
                    # Or switch between contractions
                    word = word.replace("n't", " not")
            else:
                # For bit 0: Other modifications
                if "'" in word:
                    # Remove contraction
                    word = word.replace("'s", "s")
            
            bit_index += 1
        
        result_words.append(word)
    
    return ' '.join(result_words)


def detect_embedded_bits(text: str) -> List[int]:
    """
    Detect bits potentially embedded in text.
    
    Args:
        text: Text to analyze for embedded bits
        
    Returns:
        List of detected bits
    """
    words = text.split()
    detected_bits = []
    
    for i, word in enumerate(words):
        if len(word) >= 4 and i % 3 == 0:
            # Look for modifications that might indicate embedded bits
            if "'" in word and word.endswith("'s"):
                detected_bits.append(1)
            else:
                detected_bits.append(0)
    
    return detected_bits
