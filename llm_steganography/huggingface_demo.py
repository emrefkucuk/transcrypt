"""
Advanced demonstration of LLM steganography using Hugging Face models.

This script showcases how to use real language models from Hugging Face
to generate natural text for steganographic purposes.
"""

import sys
import os
import time
import argparse
from typing import Optional, Dict, Any, List, Tuple

# Add parent directory to path to import from security.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from security import generate_secret_key, verify_secret_key

# Import steganography functions
from llm_steganography.text_generation import (
    load_model,
    generate_text,
    generate_text_with_model,
    generate_mock_text,
    TRANSFORMERS_AVAILABLE
)
from llm_steganography.steganography import (
    encode_secret_in_text,
    decode_secret_from_text,
    generate_cover_text_with_secret
)

# Define available models for demo
AVAILABLE_MODELS = [
    # "distilgpt2",        # Fast, small model (good for demo)
    # "gpt2",              # Standard GPT-2 model
    # "facebook/opt-125m", # Meta's OPT model (small)
    # "facebook/opt-350m", # Meta's OPT model (medium)
    "facebook/opt-1.3b", # Meta's OPT model (better quality)
    # "EleutherAI/pythia-410m", # Pythia model (small)
    # "EleutherAI/pythia-1b",   # Pythia model (better quality)
    # "bigscience/bloom-560m",  # Multilingual model (supports Turkish)
    # "togethercomputer/RedPajama-INCITE-Base-1B-v1", # High quality text generation
    # "stabilityai/stablelm-base-alpha-3b",  # Quality text with memory optimization
    # Add more models as needed
]

# Default text generation length
DEFAULT_TEXT_LENGTH = 1200

def print_section(title: str, char: str = "=") -> None:
    """Print a section title with separators."""
    width = 70
    print("\n" + char * width)
    print(f" {title} ".center(width - 2, char))
    print(char * width)

def print_status(message: str) -> None:
    """Print a status message."""
    print(f"[INFO] {message}")

def check_huggingface_availability() -> bool:
    """Check if Hugging Face transformers library is available."""
    if not TRANSFORMERS_AVAILABLE:
        print_section("WARNING: Hugging Face Transformers Not Available", "*")
        print("The Transformers library is not installed. This demo will use mock text.")
        print("To install the required packages, run:")
        print("pip install transformers torch")
        print("*" * 70)
        return False
    return True

def format_key(key: str) -> str:
    """Format a key for display (truncate if too long)."""
    if len(key) > 25:
        return f"{key[:10]}...{key[-10:]}"
    return key

def compare_text_generation(prompt: str, models: List[str]) -> Dict[str, str]:
    """
    Compare text generation across different models.
    
    Args:
        prompt: Text prompt for generation
        models: List of model names to compare
        
    Returns:
        Dictionary mapping model names to generated texts
    """
    results = {}
    
    # Always include mock text for comparison
    results["mock"] = generate_mock_text(prompt)
    print_status(f"Generated mock text: {len(results['mock'])} chars")
    
    if TRANSFORMERS_AVAILABLE:
        for model_name in models:
            print_status(f"Loading model: {model_name}")
            if load_model(model_name):
                start_time = time.time()
                generated_text = generate_text_with_model(prompt)
                elapsed_time = time.time() - start_time
                
                if generated_text:
                    results[model_name] = generated_text
                    print_status(f"Generated text with {model_name}: {len(generated_text)} chars in {elapsed_time:.2f}s")
                else:
                    print_status(f"Failed to generate text with {model_name}")
            else:
                print_status(f"Failed to load model: {model_name}")
    
    return results

def demonstrate_steganography_with_model(prompt: str, model_name: str = None, text_length: int = DEFAULT_TEXT_LENGTH) -> None:
    """
    Demonstrate steganography using a specific model.
    
    Args:
        prompt: Text prompt for generation
        model_name: Optional model name (if None, uses default)
        text_length: Maximum length of generated text
    """
    # Load the specific model if requested
    if model_name and TRANSFORMERS_AVAILABLE:
        load_model(model_name)
        model_info = f" using {model_name}"
    else:
        model_info = ""
    
    print_section(f"Steganography Demo{model_info}")
    print(f"Prompt: \"{prompt}\"")
    
    # Generate a secret key
    secret_key = generate_secret_key()
    print(f"Original Secret Key: {format_key(secret_key)}")
    
    # Generate cover text with the model
    start_time = time.time()
    cover_text = generate_text(prompt, text_length)
    elapsed_time = time.time() - start_time
    print(f"\nGenerated Text ({elapsed_time:.2f}s) [{len(cover_text)} chars]:\n{cover_text}\n")
    
    # Encode the secret key in the text
    print_status("Encoding secret key in text...")
    stegotext = encode_secret_in_text(secret_key, cover_text)
    print(f"\nStegotext (with hidden key):\n{stegotext}\n")
    
    # Decode the secret key from the text
    print_status("Extracting secret key from text...")
    extracted_key = decode_secret_from_text(stegotext)
    print(f"Extracted Secret Key: {format_key(extracted_key) if extracted_key else 'None'}")
    
    # Verify the keys match
    matches = verify_secret_key(extracted_key, secret_key) if extracted_key else False
    print(f"Keys Match: {'✓ Yes' if matches else '✗ No'}")

def run_multi_prompt_demo(model_name: str = None, text_length: int = DEFAULT_TEXT_LENGTH) -> None:
    """
    Run demos with different types of prompts.
    
    Args:
        model_name: Optional model name to use
        text_length: Maximum length of generated text
    """
    prompts = [
        "Explain the concept of encryption to a beginner.",
        "Discuss the ethical implications of artificial intelligence.",
        "Write a short description of a cyber security protocol.",
        "Describe the importance of privacy in the digital age.",
        "Explain how quantum computing might affect cryptography."
    ]
    
    for i, prompt in enumerate(prompts, 1):
        print_section(f"Demo {i}: {prompt[:30]}...", "-")
        demonstrate_steganography_with_model(prompt, model_name, text_length)
        
        # Small pause between demos
        if i < len(prompts):
            print("\nMoving to next demo in 2 seconds...")
            time.sleep(2)

def run_model_comparison_demo(prompt: str, text_length: int = DEFAULT_TEXT_LENGTH) -> None:
    """
    Compare steganography results across different models.
    
    Args:
        prompt: Text prompt for generation
        text_length: Maximum length of generated text
    """
    print_section("Model Comparison Demo")
    print(f"Prompt: \"{prompt}\"")
    
    # Generate a single secret key to use for all models
    secret_key = generate_secret_key()
    print(f"Secret Key: {format_key(secret_key)}")
    
    # List of models to compare (limit to 2-3 for reasonable runtime)
    models_to_compare = AVAILABLE_MODELS[:2]  # Just use the first two models
    
    # Only run comparisons if transformers is available
    if TRANSFORMERS_AVAILABLE:
        print("\nGenerating text with different models:")
        for model_name in models_to_compare:
            print_status(f"Testing model: {model_name}")
            
            # Load the model
            if not load_model(model_name):
                print(f"  Failed to load model {model_name}, skipping")
                continue
                
            # Generate cover text
            start_time = time.time()
            cover_text = generate_text_with_model(prompt, text_length)
            gen_time = time.time() - start_time
            
            if not cover_text:
                print(f"  Failed to generate text with {model_name}")
                continue
                
            print(f"  Generated {len(cover_text)} chars in {gen_time:.2f}s")
            
            # Encode/decode to test effectiveness
            stegotext = encode_secret_in_text(secret_key, cover_text)
            extracted_key = decode_secret_from_text(stegotext)
            success = verify_secret_key(extracted_key, secret_key) if extracted_key else False
            
            print(f"  Key extraction successful: {'✓' if success else '✗'}")
    else:
        print("\nTransformers library not available, skipping model comparison")

def main() -> None:
    """Main function for the HuggingFace steganography demo."""
    parser = argparse.ArgumentParser(description="Demo for LLM steganography using HuggingFace models")
    parser.add_argument("--model", "-m", type=str, help="Model name to use (e.g., distilgpt2, gpt2)")
    parser.add_argument("--prompt", "-p", type=str, help="Custom prompt for text generation")
    parser.add_argument("--compare", "-c", action="store_true", help="Run model comparison demo")
    parser.add_argument("--length", "-l", type=int, default=DEFAULT_TEXT_LENGTH, 
                        help=f"Maximum length of generated text (default: {DEFAULT_TEXT_LENGTH})")
    args = parser.parse_args()
    
    print_section("LLM Steganography with HuggingFace Demo")
    
    # Check if transformers is available
    has_transformers = check_huggingface_availability()
    
    if args.compare:
        # Run the model comparison demo
        prompt = args.prompt or "Explain the importance of secure communication."
        run_model_comparison_demo(prompt, args.length)
    elif args.prompt:
        # Run a single demo with the specified prompt and model
        demonstrate_steganography_with_model(args.prompt, args.model, args.length)
    else:
        # Run the multi-prompt demo with default or specified model
        run_multi_prompt_demo(args.model, args.length)
    
    print_section("Demo Completed")

if __name__ == "__main__":
    main()
