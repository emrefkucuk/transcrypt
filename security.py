import secrets
import hashlib
import base64
import hmac

# Güvenli secret key üretmek için
def generate_secret_key(length=32):
    """
    Cryptographically secure random token generation
    """
    return secrets.token_urlsafe(length)

# Secret key doğrulaması için
def verify_secret_key(provided_key, stored_key):
    """
    Verify if the provided key matches the stored key
    Using constant time comparison to prevent timing attacks
    """
    if not provided_key or not stored_key:
        return False
    return hmac.compare_digest(provided_key, stored_key)

# Session token için hash fonksiyonu
def hash_token(token, salt=None):
    """
    Create a secure hash of the token with an optional salt
    """
    if not salt:
        salt = secrets.token_hex(16)
    
    key = hashlib.pbkdf2_hmac(
        'sha256',
        token.encode('utf-8'),
        salt.encode('utf-8'),
        100000  # Iteration count
    )
    
    return base64.b64encode(key).decode('utf-8'), salt
