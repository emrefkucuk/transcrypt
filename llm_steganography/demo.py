"""
Demonstration script for LLM steganography module.

This script shows how to use the steganography functions to hide and extract
secret keys in/from LLM-generated text.
"""

import sys
import os
from typing import Tuple, Optional

# Add parent directory to path to import from security.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from security import generate_secret_key, verify_secret_key

# Fix imports to use absolute paths
from llm_steganography.text_generation import generate_text
from llm_steganography.steganography import (
    encode_secret_in_text,
    decode_secret_from_text,
    generate_cover_text_with_secret
)


def print_section(title: str) -> None:
    """Print a section title with separators."""
    print("\n" + "=" * 60)
    print(f" {title} ".center(60, "-"))
    print("=" * 60)


def demo_basic_encoding_decoding() -> None:
    """Demonstrate basic encoding and decoding of a secret key."""
    print_section("Basic Encoding and Decoding")
    
    # Generate a secret key
    secret_key = generate_secret_key()
    print(f"Original Secret Key: {secret_key}")
    
    # Simple cover text
    cover_text = "This is a sample text that will be used to hide a secret key. " + \
                 "The steganography algorithm will embed the key in a way that " + \
                 "preserves the natural appearance of the text. Modern steganography " + \
                 "techniques focus on maintaining statistical properties of the cover medium."
    
    print(f"\nOriginal Cover Text:\n{cover_text}")
    
    # Encode the secret key in the text
    stegotext = encode_secret_in_text(secret_key, cover_text)
    print(f"\nStegotext (with hidden key):\n{stegotext}")
    
    # Decode the secret key from the text
    extracted_key = decode_secret_from_text(stegotext)
    print(f"\nExtracted Secret Key: {extracted_key or 'None'}")
    
    # Verify the keys match
    matches = verify_secret_key(extracted_key, secret_key) if extracted_key else False
    print(f"Secret Keys Match: {matches}")


def generate_and_verify_stegotext(prompt: str) -> Tuple[str, str, Optional[str]]:
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


def demo_llm_generation() -> None:
    """Demonstrate generating text with an embedded secret key."""
    print_section("LLM Text Generation with Hidden Key")
    
    # Generate a prompt for the LLM
    prompt = "Explain how encryption works in simple terms."
    print(f"Prompt: {prompt}")
    
    # Generate text with an embedded secret key
    secret_key, stegotext, extracted_key = generate_and_verify_stegotext(prompt)
    
    print(f"\nGenerated Secret Key: {secret_key}")
    print(f"\nGenerated Text with Hidden Key:\n{stegotext}")
    print(f"\nExtracted Secret Key: {extracted_key or 'None'}")
    
    # Verify the keys match
    matches = verify_secret_key(extracted_key, secret_key) if extracted_key else False
    print(f"Secret Keys Match: {matches}")


def demo_api_key_hiding() -> None:
    """Demonstrate hiding and extracting an API key in text."""
    print_section("API Key Hiding in Natural Text")
    
    # Example API key
    api_key = "sk-1234567890abcdef1234567890abcdef"
    print(f"Original API Key: {api_key}")
    
    # Generate a cover text for the API key
    prompt = "Discuss the importance of API security."
    cover_text = generate_text(prompt)
    
    print(f"\nCover Text:\n{cover_text}")
    
    # Encode the API key
    stegotext = encode_secret_in_text(api_key, cover_text)
    print(f"\nText with Hidden API Key:\n{stegotext}")
    
    # Extract the API key
    extracted_key = decode_secret_from_text(stegotext)
    print(f"\nExtracted API Key: {extracted_key or 'None'}")
    
    # Verify it matches
    matches = api_key == extracted_key if extracted_key else False
    print(f"API Keys Match: {matches}")


def main() -> None:
    """Run demonstrations of the LLM steganography system."""
    print("LLM Steganography Demonstration")
    print("-------------------------------")
    print("This demo shows how to hide and extract secret keys in LLM-generated text.")
    
    # Run the basic demo
    demo_basic_encoding_decoding()
    
    # Run the LLM generation demo
    demo_llm_generation()
    
    # Run the API key hiding demo
    demo_api_key_hiding()
    
    print("\nAll demonstrations completed.")


if __name__ == "__main__":
    main()
