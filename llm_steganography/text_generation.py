"""
Text generation functions for LLM-based steganography.

This module provides functions to generate natural text using language models,
which will serve as cover for hiding secret keys.
"""

import numpy as np
from typing import List, Dict, Any, Optional
import random
import re
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("text_generation")

# Initialize model variables
transformer_model = None
tokenizer = None
# Silent mode flag - when True, model won't be loaded automatically
SILENT_MODE = False

# Try to import transformers library - we'll handle the case if it's not installed
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("Transformers library not found. Using mock text generation instead.")
    logger.warning("To install: pip install transformers torch")

# Default model to use from Huggingface
# DEFAULT_MODEL = "distilgpt2"  # Small but decent model
DEFAULT_MODEL = "facebook/opt-1.3b"  # Small but decent model

def load_model(model_name: str = DEFAULT_MODEL, use_4bit: bool = False, use_8bit: bool = False) -> bool:
    """
    Load the language model from Huggingface.
    
    Args:
        model_name: Name of the model to load from Huggingface
        use_4bit: Whether to use 4-bit quantization (for large models)
        use_8bit: Whether to use 8-bit quantization (for large models)
        
    Returns:
        True if model loaded successfully, False otherwise
    """
    global transformer_model, tokenizer
    
    if not TRANSFORMERS_AVAILABLE:
        logger.warning("Cannot load model: transformers library not available")
        return False
        
    try:
        logger.info(f"Loading language model: {model_name}")
        # Load the tokenizer
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # Check model size to decide on quantization
        if "7b" in model_name.lower() or "7B" in model_name or "mistral" in model_name.lower() or "llama" in model_name.lower():
            # These models are too large for 6GB VRAM without quantization
            use_4bit = True
            logger.info(f"Automatically enabling 4-bit quantization for large model: {model_name}")
        
        # Load the model with quantization if requested
        if use_4bit or use_8bit:
            try:
                from transformers import BitsAndBytesConfig
                import bitsandbytes as bnb
                
                logger.info(f"Loading {model_name} with {'4-bit' if use_4bit else '8-bit'} quantization")
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=use_4bit,
                    load_in_8bit=use_8bit if not use_4bit else False,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
                
                transformer_model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    quantization_config=quantization_config,
                    device_map="auto"
                )
            except ImportError:
                logger.warning("bitsandbytes not installed. Please install with: pip install bitsandbytes")
                logger.warning("Falling back to regular model loading without quantization")
                transformer_model = AutoModelForCausalLM.from_pretrained(model_name)
        else:
            # Regular model loading
            transformer_model = AutoModelForCausalLM.from_pretrained(model_name)
        
        logger.info(f"Successfully loaded model: {model_name}")
        return True
    except Exception as e:
        logger.error(f"Error loading model {model_name}: {str(e)}")
        transformer_model = None
        tokenizer = None
        return False

def generate_text_with_model(prompt: str, max_length: int = 500) -> str:
    """
    Generate text using a loaded Huggingface model.
    
    Args:
        prompt: The prompt to generate text from
        max_length: Maximum length of generated text (used only as a guide)
        
    Returns:
        Generated text
    """
    global transformer_model, tokenizer
    
    if transformer_model is None or tokenizer is None:
        # Try to load the model if it's not already loaded
        if not load_model():
            return None
    
    try:
        # Set up a proper text generation pipeline instead of direct model use
        generator = pipeline(
            "text-generation",
            model=transformer_model,
            tokenizer=tokenizer,
            device=0 if torch.cuda.is_available() else -1
        )
        
        # Generate text with better parameters
        # Using max_new_tokens instead of max_length to avoid truncation warnings
        max_new_tokens = max_length  # Use the provided max_length as max_new_tokens
        
        response = generator(
            prompt,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            top_k=50,
            top_p=0.95,
            temperature=0.8,
            num_return_sequences=1,
            pad_token_id=tokenizer.eos_token_id if hasattr(tokenizer, 'eos_token_id') else None,
            return_full_text=True  # Include the prompt in response
        )
        
        if not response or not isinstance(response, list) or len(response) == 0:
            logger.warning("No response generated from pipeline")
            return fallback_generation(prompt, max_length)
            
        # Extract the generated text from the response
        generated_text = response[0]['generated_text']
        
        # Return the full generated text without truncation
        return generated_text
        
    except Exception as e:
        logger.error(f"Error generating text: {str(e)}")
        return fallback_generation(prompt, max_length)

def fallback_generation(prompt: str, max_length: int = 500) -> str:
    """
    Alternative text generation method when the pipeline approach fails.
    
    Args:
        prompt: The prompt to generate text from
        max_length: Maximum length of generated text
        
    Returns:
        Generated text
    """
    global transformer_model, tokenizer
    
    try:
        # Try a different approach with manual token generation
        # Encode the prompt
        input_ids = tokenizer.encode(prompt, return_tensors="pt", add_special_tokens=True)
        
        # Create attention mask
        attention_mask = torch.ones(input_ids.shape, device=input_ids.device)
        
        # Calculate the length of the input in tokens
        input_length = len(input_ids[0])
        
        # Set max_length as input length + desired new tokens
        # This avoids truncation as it focuses on how many new tokens to generate
        total_length = input_length + max_length
        
        # Generate text without using max_length directly
        output = transformer_model.generate(
            input_ids,
            attention_mask=attention_mask,
            max_new_tokens=max_length,  # Generate this many new tokens
            num_return_sequences=1,
            no_repeat_ngram_size=2,
            do_sample=True,
            top_k=50,
            top_p=0.95,
            temperature=0.7,
            pad_token_id=tokenizer.eos_token_id,
        )
        
        # Decode the output
        generated_text = tokenizer.decode(output[0], skip_special_tokens=True)
        return generated_text
    
    except Exception as e:
        logger.error(f"Fallback generation also failed: {str(e)}")
        # If all else fails, use our mock text
        return generate_mock_text(prompt, max_length)

# Keep the mock implementation as a fallback
def generate_mock_text(prompt: str, max_length: int = 500) -> str:
    """
    Generate mock text when the real model is not available.
    
    Args:
        prompt: The prompt (incorporated into mock implementation)
        max_length: Maximum length of generated text (ignored to prevent truncation)
        
    Returns:
        Sample predefined text
    """
    # Enhanced mock texts with varied lengths and incorporating the prompt
    sample_texts = {
        "encryption": "Encryption is a fundamental technique in cybersecurity that converts readable data (plaintext) into an encoded format (ciphertext) that can only be read or processed after it's been decrypted with a key. Modern encryption relies on complex mathematical algorithms to protect sensitive information from unauthorized access. Public key infrastructure enables secure communication between parties without prior contact. When implemented correctly, these systems provide confidentiality, integrity, and authentication guarantees that are essential for secure transactions. The two primary types of encryption are symmetric, where the same key is used for encryption and decryption, and asymmetric, where different keys are used for each operation. Common encryption algorithms include AES, RSA, and ECC. As computing power increases, encryption standards must evolve to maintain security against increasingly sophisticated attacks.",
        
        "artificial intelligence": "Artificial intelligence represents a significant turning point in technological evolution, enabling machines to learn from experience, adjust to new inputs, and perform human-like tasks. The ethics of AI development raises profound questions about privacy, bias, and the future of work. As AI systems become more autonomous in making decisions that affect human lives, ensuring fairness, transparency, and accountability becomes increasingly important. Organizations must adopt comprehensive ethical frameworks that address both technical vulnerabilities and societal impacts. The balance between innovation and responsible deployment remains a key challenge in creating AI systems that benefit humanity while minimizing potential harms. Questions about data privacy, algorithmic bias, and the digital divide must be addressed through collaborative efforts between technologists, ethicists, policymakers, and affected communities.",
        
        "cyber security": "Cybersecurity protocols are structured frameworks of guidelines and practices designed to protect digital systems and sensitive information from unauthorized access and attacks. A robust protocol typically includes multiple layers of protection across networks, applications, and data. Authentication protocols verify user identities through methods like multi-factor authentication, while encryption protocols secure data transmission using advanced algorithms. Intrusion detection systems continuously monitor for suspicious activities and potential breaches, triggering automated responses when threats are detected. Regular security audits, vulnerability assessments, and penetration testing ensure the ongoing effectiveness of these protocols. As cyber threats evolve in sophistication, security protocols must be regularly updated and tested to address emerging vulnerabilities and attack vectors.",
        
        "privacy": "Privacy in the digital age has become increasingly complex and vital as our lives become more intertwined with technology. Every online interaction generates data that can be collected, analyzed, and potentially exploited by various entities. Strong data protection measures are essential for maintaining individual autonomy and preventing unauthorized surveillance or manipulation. Privacy-enhancing technologies provide tools for individuals to protect their personal information, including encryption methods, anonymous communication systems, and secure messaging applications. The regulatory landscape has evolved with laws like GDPR in Europe and CCPA in California establishing stronger consumer rights over personal data. Organizations must balance data collection needs with ethical considerations and compliance requirements. Digital literacy and awareness about privacy risks have become essential skills for navigating today's interconnected world.",
        
        "quantum computing": "Quantum computing poses both revolutionary opportunities and existential threats to modern cryptography. Unlike classical computers that use bits representing 0 or 1, quantum computers use qubits that can exist in multiple states simultaneously, enabling them to solve certain problems exponentially faster. This capability threatens many cryptographic systems that rely on the computational difficulty of problems like integer factorization and discrete logarithms. Shor's algorithm, when implemented on a sufficiently powerful quantum computer, could break RSA and ECC encryption that currently protects much of our digital infrastructure. This has accelerated the development of post-quantum cryptography—algorithms resistant to quantum attacks. Organizations are increasingly preparing for cryptographic agility, the ability to quickly transition between encryption methods as vulnerabilities emerge. The cryptographic community faces the challenge of developing, standardizing, and deploying quantum-resistant algorithms before large-scale quantum computers become a reality."
    }
    
    # Find the best matching text based on the prompt
    best_match = None
    best_score = -1
    
    for keyword, text in sample_texts.items():
        if keyword.lower() in prompt.lower():
            # Found a direct keyword match
            best_match = text
            break
        
        # Simple word overlap score
        prompt_words = set(prompt.lower().split())
        keyword_words = set(keyword.lower().split())
        overlap = len(prompt_words.intersection(keyword_words))
        
        if overlap > best_score:
            best_score = overlap
            best_match = text
    
    # If no good match, use a random text
    if best_match is None:
        best_match = random.choice(list(sample_texts.values()))
    
    # Modify the chosen text to include the prompt at the beginning
    full_text = f"{prompt}\n\n{best_match}"
    
    # Return the full text without truncation
    return full_text

def generate_text(prompt: str, max_length: int = 500) -> str:
    """
    Generate natural text using either a real language model or fallback mock text.
    
    Args:
        prompt: The initial prompt to guide text generation
        max_length: Maximum length of generated text
        
    Returns:
        Generated text
    """
    # Try to generate text with the real model
    if TRANSFORMERS_AVAILABLE:
        generated_text = generate_text_with_model(prompt, max_length)
        if generated_text and len(generated_text.strip()) > len(prompt) * 1.2:  # Ensure we got meaningful text
            return generated_text
    
    # Fall back to mock text if real generation fails or is too short
    return generate_mock_text(prompt, max_length)

def predict_next_token_distribution(text: str) -> np.ndarray:
    """
    Get probability distribution for the next token in a sequence.
    
    Args:
        text: The text context for prediction
        
    Returns:
        Numpy array representing token probability distribution
    """
    global transformer_model, tokenizer
    
    # Try to use the real model if available
    if TRANSFORMERS_AVAILABLE and transformer_model is not None and tokenizer is not None:
        try:
            # Tokenize the input text
            inputs = tokenizer.encode(text, return_tensors="pt")
            
            # Get logits for the next token
            with torch.no_grad():
                outputs = transformer_model(inputs)
                logits = outputs.logits[0, -1, :]
            
            # Convert logits to probabilities
            probabilities = torch.softmax(logits, dim=0).numpy()
            return probabilities
        except Exception as e:
            logger.error(f"Error predicting token distribution: {str(e)}")
    
    # Fall back to mock distribution
    vocab_size = 50257  # GPT-2 vocabulary size
    
    # Create a dummy distribution
    distribution = np.random.dirichlet(np.ones(vocab_size) * 0.1)
    
    # Make the distribution more realistic by concentrating probability mass
    top_indices = np.random.choice(vocab_size, 100, replace=False)
    for idx in top_indices:
        distribution[idx] *= 10
    
    # Normalize
    distribution /= distribution.sum()
    
    return distribution

# Don't try to load model at module import time - we'll load it when needed
# The main.py file will update SILENT_MODE before any function calls
