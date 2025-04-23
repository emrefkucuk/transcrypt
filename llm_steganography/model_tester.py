"""
Model Tester for Text Generation

This script tests various language models for text generation capabilities.
It allows comparing output from different models using the same prompts.
"""

import os
import time
import argparse
from typing import List, Dict, Optional
import torch

# Import the necessary modules from text_generation
from text_generation import (
    load_model,
    generate_text_with_model,
    generate_mock_text,
    TRANSFORMERS_AVAILABLE
)

# Define the models to test
DEFAULT_MODELS = [
    # Original recommendations
    "bigscience/bloom-560m",    # Multilingual model (good for Turkish)
    "EleutherAI/pythia-1b",     # Good for coherent text generation
    "togethercomputer/RedPajama-INCITE-Base-1B-v1",  # Well-balanced model
    
    # New additional models
    "microsoft/phi-1_5",        # 1.3B lightweight but very efficient model
    "stabilityai/stablelm-tuned-alpha-3b", # Advanced model with 4-bit quantization option
    "databricks/dolly-v2-3b",   # Instruction-following model for excellent responses
    "EleutherAI/gpt-neo-1.3B",  # Classic but effective with 1.3B parameters
    "huggyllama/llama-7b-qlora", # Quantized LLaMA model (needs 4-bit quantization)
    "mistralai/Mistral-7B-v0.1", # Excellent perform/size ratio (needs 4/8-bit quant)
]

# Sample prompts for testing (including some in Turkish)
DEFAULT_PROMPTS = [
    "Yapay zeka teknolojilerinin günlük hayatımıza etkileri nelerdir?",
    "Şifreleme teknolojilerinin önemini anlatan bir makale yazın.",
    "Write a short essay on the importance of data privacy.",
    "Explain how quantum computing might affect modern cryptography."
]

class ModelTester:
    """Class to handle model testing functionality."""
    
    def __init__(self, models: List[str] = None, prompts: List[str] = None, 
                 max_length: int = 2000, save_output: bool = False):
        """
        Initialize the model tester.
        
        Args:
            models: List of model names to test
            prompts: List of prompts to test with
            max_length: Maximum length of generated text
            save_output: Whether to save output to files
        """
        self.models = models or DEFAULT_MODELS
        self.prompts = prompts or DEFAULT_PROMPTS
        self.max_length = max_length
        self.save_output = save_output
        
        # Check if CUDA is available
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")
        
        # Get GPU info if available
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            memory_allocated = torch.cuda.memory_allocated(0) / 1024**2  # Convert to MB
            memory_total = torch.cuda.get_device_properties(0).total_memory / 1024**2
            print(f"GPU: {gpu_name}")
            print(f"Memory: {memory_allocated:.2f}MB / {memory_total:.2f}MB")
    
    def print_section(self, title: str, char: str = "=") -> None:
        """Print a section title with separators."""
        width = 80
        print("\n" + char * width)
        print(f" {title} ".center(width - 2, char))
        print(char * width)
    
    def test_model(self, model_name: str, prompt: str) -> Optional[Dict]:
        """
        Test a specific model with a specific prompt.
        
        Args:
            model_name: Name of the model to test
            prompt: Text prompt for generation
            
        Returns:
            Dictionary with test results or None if failed
        """
        if not TRANSFORMERS_AVAILABLE:
            print(f"Transformers library not available, using mock text instead")
            generated_text = generate_mock_text(prompt, self.max_length)
            return {"text": generated_text, "time": 0, "model": "mock"}
        
        print(f"Loading model: {model_name}")
        start_load_time = time.time()
        
        # Automatically use quantization for larger models
        use_4bit = False
        if "7b" in model_name.lower() or "7B" in model_name or "mistral" in model_name.lower() or "llama" in model_name.lower() or model_name.endswith("-3b") or "-3B" in model_name:
            print(f"Using 4-bit quantization for {model_name}")
            use_4bit = True
            
            # Check if bitsandbytes is installed
            try:
                import bitsandbytes
                print("bitsandbytes is installed, continuing with quantization")
            except ImportError:
                print("WARNING: bitsandbytes not installed. Please install with: pip install bitsandbytes")
                print("Some larger models may not load without quantization.")
        
        success = load_model(model_name, use_4bit=use_4bit)
        load_time = time.time() - start_load_time
        
        if not success:
            print(f"Failed to load model: {model_name}")
            return None
        
        print(f"Model loaded in {load_time:.2f}s, generating text...")
        start_gen_time = time.time()
        generated_text = generate_text_with_model(prompt, self.max_length)
        gen_time = time.time() - start_gen_time
        total_time = time.time() - start_load_time
        
        if not generated_text:
            print(f"Failed to generate text with {model_name}")
            return None
        
        result = {
            "model": model_name,
            "prompt": prompt,
            "text": generated_text,
            "load_time": load_time,
            "generation_time": gen_time,
            "total_time": total_time,
            "length": len(generated_text)
        }
        
        print(f"Generated {len(generated_text)} chars in {gen_time:.2f}s")
        return result
    
    def save_result_to_file(self, result: Dict) -> None:
        """
        Save a test result to a file.
        
        Args:
            result: Test result dictionary
        """
        if not self.save_output:
            return
            
        # Create output directory if it doesn't exist
        output_dir = os.path.join(os.path.dirname(__file__), "model_outputs")
        os.makedirs(output_dir, exist_ok=True)
        
        # Create a filename based on model and prompt
        model_name = result["model"].split("/")[-1]
        prompt_preview = result["prompt"][:20].replace(" ", "_").replace("?", "")
        filename = f"{model_name}_{prompt_preview}.txt"
        filepath = os.path.join(output_dir, filename)
        
        # Write the result to the file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"Model: {result['model']}\n")
            f.write(f"Prompt: {result['prompt']}\n")
            f.write(f"Generation time: {result['generation_time']:.2f}s\n\n")
            f.write(result["text"])
        
        print(f"Output saved to: {filepath}")
    
    def display_result(self, result: Dict) -> None:
        """
        Display a test result.
        
        Args:
            result: Test result dictionary
        """
        self.print_section(f"Result: {result['model']}")
        print(f"Prompt: \"{result['prompt']}\"")
        print(f"Generation time: {result['generation_time']:.2f}s")
        print(f"Total time: {result['total_time']:.2f}s")
        print(f"Output length: {result['length']} characters\n")
        
        # Print the generated text
        print("Generated text:")
        print("-" * 80)
        print(result["text"])
        print("-" * 80)
    
    def run_tests(self) -> None:
        """Run all tests for all models and prompts."""
        if not TRANSFORMERS_AVAILABLE:
            print("WARNING: Transformers library not available. Using mock text instead.")
            print("To install: pip install transformers torch")
        
        for i, prompt in enumerate(self.prompts):
            self.print_section(f"Testing Prompt {i+1}: {prompt[:30]}...", "-")
            
            for model_name in self.models:
                result = self.test_model(model_name, prompt)
                
                if result:
                    self.display_result(result)
                    self.save_result_to_file(result)
                
                # Free up GPU memory
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            
            print("\n")

def main():
    """Main function to run the model tester."""
    parser = argparse.ArgumentParser(description="Test language models for text generation")
    
    parser.add_argument("--models", "-m", nargs="+", default=DEFAULT_MODELS,
                      help="List of models to test")
    
    parser.add_argument("--prompts", "-p", nargs="+", default=DEFAULT_PROMPTS,
                      help="List of prompts to test with")
    
    parser.add_argument("--length", "-l", type=int, default=500,
                      help="Maximum length of generated text")
    
    parser.add_argument("--save", "-s", action="store_true",
                      help="Save output to files")
    
    parser.add_argument("--list", action="store_true",
                      help="List available models and exit")
    
    args = parser.parse_args()
    
    if args.list:
        if TRANSFORMERS_AVAILABLE:
            from transformers import AutoModel
            print("Available models from Hugging Face that fit in 6GB VRAM:")
            for model in DEFAULT_MODELS:
                print(f"- {model}")
        else:
            print("Transformers library not available. Cannot list models.")
        return
    
    tester = ModelTester(args.models, args.prompts, args.length, args.save)
    tester.run_tests()

if __name__ == "__main__":
    main()