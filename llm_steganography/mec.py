"""
Minimum Entropy Coupling (MEC) implementation for text steganography.

This module provides the core functionality for coupling probability distributions
to embed information in text while preserving statistical properties.
"""

import numpy as np
from typing import List, Dict, Tuple, Any


class MinimumEntropyCoupler:
    """
    Implements the Minimum Entropy Coupling algorithm to embed and extract
    hidden messages in/from text while maintaining statistical properties.
    """
    
    def __init__(self, vocabulary_size: int = 50257):  # Default GPT-2 vocabulary size
        self.vocabulary_size = vocabulary_size
        self.bit_embedding_map = None
        
    def generate_coupling_matrix(self, cover_distribution: np.ndarray, message_distribution: np.ndarray) -> np.ndarray:
        """
        Generate a coupling matrix between cover text and message distributions.
        
        Args:
            cover_distribution: Probability distribution of the cover text
            message_distribution: Probability distribution of the message
            
        Returns:
            A coupling matrix that minimizes joint entropy
        """
        # Ensure distributions are normalized
        cover_distribution = cover_distribution / np.sum(cover_distribution)
        message_distribution = message_distribution / np.sum(message_distribution)
        
        m = len(cover_distribution)
        n = len(message_distribution)
        
        # Initialize coupling matrix
        coupling = np.zeros((m, n))
        
        # Implement greedy MEC algorithm
        remaining_cover_prob = cover_distribution.copy()
        remaining_message_prob = message_distribution.copy()
        
        # Iteratively assign probabilities to minimize entropy
        while np.sum(remaining_cover_prob) > 1e-10:
            # Find indices with highest remaining probabilities
            i = np.argmax(remaining_cover_prob)
            j = np.argmax(remaining_message_prob)
            
            # Assign coupling probability
            coupling_prob = min(remaining_cover_prob[i], remaining_message_prob[j])
            coupling[i, j] += coupling_prob
            
            # Update remaining probabilities
            remaining_cover_prob[i] -= coupling_prob
            remaining_message_prob[j] -= coupling_prob
        
        return coupling
    
    def create_bit_embedding_map(self, top_k: int = 100) -> Dict[int, int]:
        """
        Create a mapping to embed bits in token choices.
        
        Args:
            top_k: Number of top tokens to consider for each position
            
        Returns:
            Dictionary mapping token indices to bit values (0 or 1)
        """
        # For simplicity, alternate bit assignments for tokens
        bit_map = {}
        for i in range(self.vocabulary_size):
            # Assign 0 or 1 based on token index parity
            bit_map[i] = i % 2
        
        self.bit_embedding_map = bit_map
        return bit_map
    
    def encode_bits_in_token_choices(self, 
                                     token_probabilities: np.ndarray, 
                                     bits_to_encode: List[int], 
                                     top_k: int = 10) -> List[int]:
        """
        Encode bits by selecting specific tokens when generating text.
        
        Args:
            token_probabilities: Probability distribution over vocabulary for next token
            bits_to_encode: List of bits (0 or 1) to encode
            top_k: Number of top tokens to consider for each position
            
        Returns:
            List of selected token indices that encode the given bits
        """
        if self.bit_embedding_map is None:
            self.create_bit_embedding_map(top_k)
        
        # Get top-k token indices by probability
        top_indices = np.argsort(token_probabilities)[-top_k:]
        
        selected_tokens = []
        bit_position = 0
        
        # For each position where we need to encode a bit
        while bit_position < len(bits_to_encode) and bit_position < len(top_indices):
            bit_to_encode = bits_to_encode[bit_position]
            
            # Find tokens in top-k that encode the desired bit
            matching_tokens = [idx for idx in top_indices 
                              if self.bit_embedding_map.get(idx, 0) == bit_to_encode]
            
            if matching_tokens:
                # Choose token with highest probability among matching tokens
                token_probs = [token_probabilities[idx] for idx in matching_tokens]
                selected_token = matching_tokens[np.argmax(token_probs)]
                selected_tokens.append(selected_token)
            else:
                # Fallback if no matching token found
                selected_tokens.append(top_indices[-1])  # Use highest probability token
            
            bit_position += 1
        
        return selected_tokens
    
    def extract_bits_from_tokens(self, tokens: List[int], num_bits: int) -> List[int]:
        """
        Extract bits from token sequence based on the embedding map.
        
        Args:
            tokens: List of token indices
            num_bits: Number of bits to extract
            
        Returns:
            List of extracted bits (0 or 1)
        """
        if self.bit_embedding_map is None:
            self.create_bit_embedding_map()
        
        extracted_bits = []
        
        for token in tokens:
            if len(extracted_bits) >= num_bits:
                break
                
            extracted_bits.append(self.bit_embedding_map.get(token, 0))
        
        return extracted_bits[:num_bits]
