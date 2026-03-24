import re

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


def normalize_pem(data: bytes) -> bytes:
    """Normalize PEM data by ensuring proper newlines between header, base64 body, and footer."""
    text = data.decode('utf-8', errors='replace').strip()
    match = re.match(
        r'(-----BEGIN [A-Z ]+-----)\s*(.*?)\s*(-----END [A-Z ]+-----)',
        text,
        re.DOTALL
    )
    if not match:
        return data
    header, body, footer = match.groups()
    body_clean = re.sub(r'\s+', '', body)
    lines = [body_clean[i:i+64] for i in range(0, len(body_clean), 64)]
    return (header + '\n' + '\n'.join(lines) + '\n' + footer + '\n').encode('utf-8')


def encrypt_certificate(cert_data: bytes) -> bytes:
    """Encripta un certificado o clave privada. Normaliza PEM antes de encriptar."""
    f = get_fernet()
    return f.encrypt(normalize_pem(cert_data))


def decrypt_certificate(encrypted_data: bytes) -> bytes:
    """Desencripta un certificado o clave privada. Normaliza PEM tras desencriptar."""
    f = get_fernet()
    return normalize_pem(f.decrypt(encrypted_data))
