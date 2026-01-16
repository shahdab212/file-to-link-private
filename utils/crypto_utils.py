
import base64
import hashlib
from typing import Optional
import logging
from config import Config

logger = logging.getLogger(__name__)

class CryptoUtils:
    """Utilities for ID encryption and obfuscation"""
    
    @staticmethod
    def _get_key_bytes() -> bytes:
        """Derive a fixed-size key from the secret key"""
        # Create a 32-byte key from the secret string
        return hashlib.sha256(Config.SECRET_KEY.encode()).digest()

    @classmethod
    def encrypt_id(cls, plain_id: str) -> str:
        """
        Encrypt/Obfuscate a file ID to make it opaque.
        Uses a custom XOR + Base64 scheme to keep URLs relatively short
        while preventing simple scraping.
        """
        try:
            key = cls._get_key_bytes()
            # Convert ID to bytes
            id_bytes = plain_id.encode()
            
            # XOR encryption
            xor_bytes = bytearray(len(id_bytes))
            for i in range(len(id_bytes)):
                xor_bytes[i] = id_bytes[i] ^ key[i % len(key)]
                
            # Add a simple checksum/magic byte to verify validity later
            magic = b'\x01' # Version 1
            final_bytes = magic + xor_bytes
            
            # Base64 encode (URL safe)
            return base64.urlsafe_b64encode(final_bytes).decode().rstrip('=')
        except Exception as e:
            logger.error(f"Error encrypting ID: {e}")
            return plain_id

    @classmethod
    def decrypt_id(cls, encrypted_id: str) -> Optional[str]:
        """
        Decrypt/De-obfuscate a file ID.
        Returns None if decryption fails.
        """
        try:
            # Pad base64 if needed
            padding = len(encrypted_id) % 4
            if padding:
                encrypted_id += '=' * (4 - padding)
                
            decoded_bytes = base64.urlsafe_b64decode(encrypted_id)
            
            # Check magic byte
            if len(decoded_bytes) < 2 or decoded_bytes[0] != 1:
                return None
                
            xor_bytes = decoded_bytes[1:]
            key = cls._get_key_bytes()
            
            # XOR decryption
            plain_bytes = bytearray(len(xor_bytes))
            for i in range(len(xor_bytes)):
                plain_bytes[i] = xor_bytes[i] ^ key[i % len(key)]
                
            return plain_bytes.decode()
            
        except Exception as e:
            # logger.debug(f"Failed to decrypt ID {encrypted_id}: {e}")
            return None
