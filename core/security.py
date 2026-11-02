from cryptography.fernet import Fernet
from core.config import config


def get_cipher() -> Fernet:
    """Fernet cipher olish"""
    key = config.ENCRYPTION_KEY.get_secret_value()
    return Fernet(key)


def encrypt_text(text: str) -> str:
    """Matnni shifrlash"""
    cipher = get_cipher()
    encrypted = cipher.encrypt(text.encode('utf-8'))
    return encrypted.decode('utf-8')


def decrypt_text(encrypted_text: str) -> str:
    """Shifrlangan matnni ochish"""
    cipher = get_cipher()
    decrypted = cipher.decrypt(encrypted_text.encode('utf-8'))
    return decrypted.decode('utf-8')
