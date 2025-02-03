from cryptography.fernet import Fernet
import os

class ConfigManager:
    def __init__(self):
        self.key = os.getenv("CONFIG_KEY").encode()
        self.cipher = Fernet(self.key)
        
    def encrypt_value(self, value: str) -> bytes:
        return self.cipher.encrypt(value.encode())
    
    def decrypt_value(self, encrypted: bytes) -> str:
        return self.cipher.decrypt(encrypted).decode()
    
    def rotate_key(self, new_key: str):
        # Implementation for key rotation
        pass