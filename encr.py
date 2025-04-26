# secure_transfer.py
# Module for secure file encryption, decryption and integrity verification

import os
import base64
import hashlib
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from typing import Tuple, Dict, Any, Union, Optional


def generate_aes_key(key_size: int = 32) -> bytes:
    """
    Generate a random AES key.
    
    Args:
        key_size: Size of the key in bytes (32 = 256 bits, 16 = 128 bits)
        
    Returns:
        Random bytes to be used as AES key
    """
    return os.urandom(key_size)  # Uses secure random number generator


def generate_rsa_key_pair(key_size: int = 2048) -> Tuple[bytes, bytes]:
    """
    Generate an RSA key pair.
    
    Args:
        key_size: Size of the RSA key in bits
        
    Returns:
        Tuple containing (private_key_pem, public_key_pem)
    """
    # Generate a private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,  # Standard value for RSA public exponent
        key_size=key_size,
        backend=default_backend()
    )
    
    # Get the public key
    public_key = private_key.public_key()
    
    # Serialize the keys to PEM format
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return private_key_pem, public_key_pem


def encrypt_aes_key_with_rsa(aes_key: bytes, public_key_pem: bytes) -> bytes:
    """
    Encrypt an AES key using an RSA public key.
    
    Args:
        aes_key: The AES key to encrypt
        public_key_pem: RSA public key in PEM format
        
    Returns:
        RSA-encrypted AES key
    """
    # Load the public key from PEM format
    public_key = serialization.load_pem_public_key(
        public_key_pem,
        backend=default_backend()
    )
    
    # Encrypt the AES key with the RSA public key using OAEP padding with SHA256
    encrypted_key = public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    
    return encrypted_key


def decrypt_aes_key_with_rsa(encrypted_aes_key: bytes, private_key_pem: bytes) -> bytes:
    """
    Decrypt an AES key using an RSA private key.
    
    Args:
        encrypted_aes_key: RSA-encrypted AES key
        private_key_pem: RSA private key in PEM format
        
    Returns:
        Decrypted AES key
    """
    # Load the private key from PEM format
    private_key = serialization.load_pem_private_key(
        private_key_pem,
        password=None,  # No password protection for this example
        backend=default_backend()
    )
    
    # Decrypt the AES key using the same padding scheme as encryption
    decrypted_key = private_key.decrypt(
        encrypted_aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    
    return decrypted_key


def calculate_file_hash(file_data: bytes) -> str:
    """
    Calculate SHA-256 hash of file data for integrity verification.
    
    Args:
        file_data: Raw bytes of the file
        
    Returns:
        Hex string representation of the SHA-256 hash
    """
    sha256 = hashlib.sha256()
    sha256.update(file_data)
    return sha256.hexdigest()


def verify_file_integrity(file_data: bytes, original_hash: str) -> bool:
    """
    Verify file integrity by comparing hash values.
    
    Args:
        file_data: Raw bytes of the file to verify
        original_hash: Original SHA-256 hash to compare against
        
    Returns:
        Boolean indicating if the file is intact (True) or corrupted (False)
    """
    calculated_hash = calculate_file_hash(file_data)
    return calculated_hash == original_hash


def encrypt_file_with_aes(file_data: bytes, aes_key: bytes) -> Dict[str, bytes]:
    """
    Encrypt a file using AES-256-GCM.
    
    Args:
        file_data: Raw bytes of the file to encrypt
        aes_key: AES key for encryption
        
    Returns:
        Dictionary containing encrypted data, iv (initialization vector), and tag
    """
    # Generate a random initialization vector
    # 96 bits (12 bytes) is the recommended IV length for GCM mode
    iv = os.urandom(12)
    
    # Create an encryptor object with AES-GCM mode
    # GCM mode provides both confidentiality and authenticity
    encryptor = Cipher(
        algorithms.AES(aes_key),
        modes.GCM(iv),
        backend=default_backend()
    ).encryptor()
    
    # Encrypt the file data
    encrypted_data = encryptor.update(file_data) + encryptor.finalize()
    
    # Return a dictionary with all components needed for decryption
    return {
        'encrypted_data': encrypted_data,
        'iv': iv,
        'tag': encryptor.tag  # Authentication tag for GCM mode to verify integrity
    }


def decrypt_file_with_aes(encrypted_package: Dict[str, bytes], aes_key: bytes) -> bytes:
    """
    Decrypt a file using AES-256-GCM.
    
    Args:
        encrypted_package: Dictionary containing encrypted data, iv, and tag
        aes_key: AES key for decryption
        
    Returns:
        Raw bytes of the decrypted file
    """
    # Extract components from the encrypted package
    encrypted_data = encrypted_package['encrypted_data']
    iv = encrypted_package['iv']
    tag = encrypted_package['tag']
    
    # Create a decryptor object with the same parameters
    # The tag is provided for authentication - an exception will be raised if tampering is detected
    decryptor = Cipher(
        algorithms.AES(aes_key),
        modes.GCM(iv, tag),
        backend=default_backend()
    ).decryptor()
    
    # Decrypt the file data
    decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()
    
    return decrypted_data


def generate_chacha_key() -> bytes:
    """
    Generate a random ChaCha20-Poly1305 key.
    
    Returns:
        Random bytes to be used as ChaCha20 key (32 bytes)
    """
    return os.urandom(32)  # ChaCha20 requires a 32-byte key


def encrypt_file_with_chacha(file_data: bytes, chacha_key: bytes) -> Dict[str, bytes]:
    """
    Encrypt a file using ChaCha20-Poly1305.
    
    Args:
        file_data: Raw bytes of the file to encrypt
        chacha_key: ChaCha20 key for encryption
        
    Returns:
        Dictionary containing encrypted data and nonce
    """
    # Generate a random nonce
    nonce = os.urandom(12)  # 96 bits for ChaCha20Poly1305
    
    # Create ChaCha20Poly1305 cipher
    cipher = ChaCha20Poly1305(chacha_key)
    
    # Encrypt the file data
    # The tag is automatically included in the ciphertext with this API
    encrypted_data = cipher.encrypt(nonce, file_data, None)
    
    return {
        'encrypted_data': encrypted_data,
        'nonce': nonce
    }


def decrypt_file_with_chacha(encrypted_package: Dict[str, bytes], chacha_key: bytes) -> bytes:
    """
    Decrypt a file using ChaCha20-Poly1305.
    
    Args:
        encrypted_package: Dictionary containing encrypted data and nonce
        chacha_key: ChaCha20 key for decryption
        
    Returns:
        Raw bytes of the decrypted file
    """
    # Extract components from the encrypted package
    encrypted_data = encrypted_package['encrypted_data']
    nonce = encrypted_package['nonce']
    
    # Create ChaCha20Poly1305 cipher
    cipher = ChaCha20Poly1305(chacha_key)
    
    # Decrypt the file data
    # This will also verify the authentication tag
    decrypted_data = cipher.decrypt(nonce, encrypted_data, None)
    
    return decrypted_data


def process_file_for_sending(file_data: bytes, receiver_public_key: bytes) -> Dict[str, Any]:
    """
    Process a file for secure sending:
    1. Generate AES key
    2. Encrypt file with AES
    3. Encrypt AES key with receiver's RSA public key
    4. Calculate file hash for integrity
    
    Args:
        file_data: Raw bytes of the file to send
        receiver_public_key: Receiver's RSA public key in PEM format
        
    Returns:
        Dictionary containing all data needed for secure transfer
    """
    # Calculate original hash for integrity checking
    original_hash = calculate_file_hash(file_data)
    
    # Generate a random AES key for symmetric encryption
    # AES is used for file encryption because it's much faster than RSA for large data
    aes_key = generate_aes_key()
    
    # Encrypt the file with the AES key
    encrypted_package = encrypt_file_with_aes(file_data, aes_key)
    
    # Encrypt the AES key with the receiver's public RSA key
    # This is the hybrid cryptosystem approach: 
    # - AES for the large file data (symmetric)
    # - RSA for the small AES key (asymmetric)
    encrypted_aes_key = encrypt_aes_key_with_rsa(
        aes_key, 
        receiver_public_key
    )
    
    # Prepare the transfer package with all required components
    transfer_package = {
        'encrypted_data': encrypted_package['encrypted_data'],
        'iv': encrypted_package['iv'],
        'tag': encrypted_package['tag'],
        'encrypted_aes_key': encrypted_aes_key,
        'original_hash': original_hash
    }
    
    return transfer_package


def process_received_file(transfer_package: Dict[str, Any], private_key: bytes) -> Dict[str, Any]:
    """
    Process a received encrypted file:
    1. Decrypt the AES key using RSA private key
    2. Decrypt the file using the AES key
    3. Verify file integrity with hash
    
    Args:
        transfer_package: Dictionary containing all encrypted file data
        private_key: Receiver's RSA private key in PEM format
        
    Returns:
        Dictionary with decrypted file and integrity verification result
    """
    # Extract components from the transfer package
    encrypted_data = transfer_package['encrypted_data']
    iv = transfer_package['iv']
    tag = transfer_package['tag']
    encrypted_aes_key = transfer_package['encrypted_aes_key']
    original_hash = transfer_package['original_hash']
    
    # Recreate the encrypted package for the decryption function
    encrypted_package = {
        'encrypted_data': encrypted_data,
        'iv': iv,
        'tag': tag
    }
    
    # Decrypt the AES key with the private RSA key
    # Only the owner of the private key can decrypt this
    aes_key = decrypt_aes_key_with_rsa(encrypted_aes_key, private_key)
    
    # Decrypt the file with the now-decrypted AES key
    decrypted_data = decrypt_file_with_aes(encrypted_package, aes_key)
    
    # Verify file integrity using the original hash
    # This ensures the file wasn't corrupted during transfer
    is_intact = verify_file_integrity(decrypted_data, original_hash)
    
    return {
        'decrypted_data': decrypted_data,
        'integrity_verified': is_intact
    }
