"""
LLM Steganography Package

This package provides tools for hiding and extracting secret keys in/from LLM-generated text
using Minimum Entropy Coupling (MEC) techniques.
"""

from .steganography import encode_secret_in_text, decode_secret_from_text, generate_cover_text_with_secret

__all__ = [
    'encode_secret_in_text',
    'decode_secret_from_text',
    'generate_cover_text_with_secret'
]
