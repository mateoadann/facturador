from cryptography.fernet import Fernet
from flask import current_app


def get_fernet():
    key = current_app.config['ENCRYPTION_KEY']
    if len(key) < 32:
        key = key.ljust(32, '0')
    elif len(key) > 32:
        key = key[:32]

    import base64
    key_bytes = base64.urlsafe_b64encode(key.encode())
    return Fernet(key_bytes)


def encrypt_certificate(cert_data: bytes) -> bytes:
    """Encripta un certificado o clave privada."""
    f = get_fernet()
    return f.encrypt(cert_data)


def decrypt_certificate(encrypted_data: bytes) -> bytes:
    """Desencripta un certificado o clave privada."""
    f = get_fernet()
    return f.decrypt(encrypted_data)
